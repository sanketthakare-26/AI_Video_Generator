"""
Local Piper TTS Voice Generation Service.

Hardware target: CPU-optimized inference.
Memory strategy:
  - Lazy load on first request
  - Unload CogVideoX before generating speech if loaded
  - Generation mutex lock to prevent concurrent ONNX synthesis
  - WAV validation using Python wave module (channels, sample rate, duration)
  - Explicit unload support to release CPU memory
"""
from __future__ import annotations

import gc
import os
import threading
import time
import wave
from pathlib import Path
from typing import Any, Dict, Optional

import torch

from app.config.settings import settings
from app.utils.logger import logger

_TTS_GENERATION_LOCK = threading.Lock()


class LocalTTSService:
    """Local Piper Text-to-Speech synthesis service."""

    def __init__(self):
        self.voice = None
        self.is_loaded = False
        self._is_generating = False
        self._loaded_model_path: Optional[str] = None

    def get_model_path(self) -> Path:
        """Resolve model path against project root or absolute path."""
        p = Path(settings.piper_model_path)
        if not p.is_absolute():
            p = settings.base_dir / p
        return p

    def get_config_path(self) -> Path:
        """Resolve JSON config path matching the ONNX model."""
        model_path = self.get_model_path()
        return model_path.with_suffix(model_path.suffix + ".json")

    def get_device_info(self) -> Dict[str, Any]:
        """Return TTS service status and model metadata without loading."""
        model_path = self.get_model_path()
        model_exists = model_path.exists() and model_path.stat().st_size > 0
        config_path = self.get_config_path()
        config_exists = config_path.exists() and config_path.stat().st_size > 0

        return {
            "service": "Piper TTS (Local)",
            "available": model_exists and config_exists,
            "loaded": self.is_loaded,
            "is_generating": self._is_generating,
            "model_path": str(model_path),
            "model_exists": model_exists,
            "config_exists": config_exists,
            "sample_rate": settings.piper_sample_rate,
            "device": "cpu",
        }

    def load_model(self) -> None:
        """Lazily load Piper ONNX voice model."""
        if self.is_loaded and self.voice is not None:
            return

        model_path = self.get_model_path()
        config_path = self.get_config_path()

        if not model_path.exists() or model_path.stat().st_size == 0:
            raise FileNotFoundError(
                f"Piper voice model not found at '{model_path}'. "
                f"Please run 'python scripts/download_piper.py' to download the model."
            )

        if not config_path.exists() or config_path.stat().st_size == 0:
            raise FileNotFoundError(
                f"Piper voice config not found at '{config_path}'. "
                f"Please run 'python scripts/download_piper.py' to download the config."
            )

        from piper import PiperVoice

        logger.info(f"[PiperTTS] Loading voice model from {model_path}...")
        t0 = time.time()
        try:
            self.voice = PiperVoice.load(
                model_path=str(model_path),
                config_path=str(config_path),
                use_cuda=False,  # Piper runs CPU-friendly
            )
            self.is_loaded = True
            self._loaded_model_path = str(model_path)
            elapsed = time.time() - t0
            logger.info(f"[PiperTTS] Model loaded in {elapsed:.2f}s.")
        except Exception as exc:
            self.is_loaded = False
            self.voice = None
            logger.error(f"[PiperTTS] Failed to load Piper model: {exc}")
            raise

    def unload_model(self) -> None:
        """Unload Piper voice model and reclaim CPU memory."""
        if not self.is_loaded:
            return
        logger.info("[PiperTTS] Unloading model...")
        if self.voice is not None:
            del self.voice
            self.voice = None
        self.is_loaded = False
        self._loaded_model_path = None
        gc.collect()
        logger.info("[PiperTTS] Model unloaded.")

    def generate_audio(
        self,
        text: str,
        output_path: Path,
        language: str = "en",
        length_scale: Optional[float] = None,
        noise_scale: Optional[float] = None,
        noise_w_scale: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize speech from text and save as WAV audio file.
        Returns a result dict with success, audio_url/path, duration, and metrics.
        """
        # 1. Validation
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            return {
                "success": False,
                "error": "Input text cannot be empty.",
                "error_type": "ValidationError",
            }

        # 2. Mutex generation lock
        if not _TTS_GENERATION_LOCK.acquire(blocking=False):
            return {
                "success": False,
                "error": "Voice generation already in progress.",
                "error_type": "BusyError",
            }

        self._is_generating = True
        t_start = time.time()

        try:
            # 3. Memory safety: Unload CogVideoX if loaded
            from app.services.video_service import cogvideo_service
            if cogvideo_service.is_loaded:
                logger.info("[PiperTTS] CogVideoX is loaded. Unloading it to conserve memory before TTS.")
                cogvideo_service.unload_model()
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            # 4. Ensure destination folder exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 5. Load model (lazy)
            t_load = time.time()
            self.load_model()
            load_elapsed = time.time() - t_load

            # 6. Configure synthesis parameters
            from piper.config import SynthesisConfig
            syn_config = SynthesisConfig(
                length_scale=length_scale or settings.piper_length_scale,
                noise_scale=noise_scale or settings.piper_noise_scale,
                noise_w_scale=noise_w_scale or settings.piper_noise_w_scale,
            )


            logger.info(f"[PiperTTS] Synthesizing ({len(cleaned_text)} chars): '{cleaned_text[:60]}...'")
            t_gen = time.time()

            with wave.open(str(output_path), "wb") as wav_file:
                self.voice.synthesize_wav(
                    cleaned_text,
                    wav_file,
                    syn_config=syn_config,
                    set_wav_format=True,
                )

            gen_elapsed = time.time() - t_gen
            total_elapsed = time.time() - t_start

            # 7. Validate generated WAV file
            if not output_path.exists() or output_path.stat().st_size == 0:
                raise RuntimeError("Synthesis failed: Output WAV file was not created or is empty.")

            with wave.open(str(output_path), "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                duration = round(n_frames / float(framerate), 2) if framerate > 0 else 0.0

            if duration <= 0:
                raise RuntimeError(f"Synthesized WAV file has invalid duration: {duration}s.")

            file_size = output_path.stat().st_size
            logger.info(
                f"[PiperTTS] Successfully generated {output_path.name} "
                f"({duration}s, {framerate}Hz, {file_size / 1024:.1f} KB) in {gen_elapsed:.2f}s."
            )

            return {
                "success": True,
                "audio_path": str(output_path),
                "audio_url": f"/api/audio/{output_path.name}",
                "duration": duration,
                "sample_rate": framerate,
                "channels": n_channels,
                "sample_width": sampwidth,
                "frames": n_frames,
                "file_size_bytes": file_size,
                "model_load_time": round(load_elapsed, 2),
                "generation_time": round(gen_elapsed, 2),
                "total_time": round(total_elapsed, 2),
            }

        except Exception as exc:
            logger.error(f"[PiperTTS] Voice generation error: {exc}", exc_info=True)
            return {
                "success": False,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
        finally:
            self._is_generating = False
            _TTS_GENERATION_LOCK.release()


# Module-level singleton
tts_service = LocalTTSService()
