"""CogVideoX-2B Local Video Generation Service.

Hardware target: NVIDIA RTX 2050 Laptop GPU (~4 GB VRAM), 8 GB RAM.
Memory strategy:
  - Lazy load (only when a request arrives, never at startup)
  - enable_sequential_cpu_offload() — model layers stream CPU→GPU one at a time
  - vae.enable_slicing() + vae.enable_tiling() — reduce peak VRAM for encoding/decoding
  - Generation lock — only one video can be generated at a time
  - Explicit unload (del references, gc.collect, cuda.empty_cache) after generation
  - NEVER load simultaneously with Qwen
"""
from __future__ import annotations

import gc
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import torch

from app.config.settings import settings
from app.utils.logger import logger

# Import diffusers lazily inside methods to keep FastAPI startup fast
# (they are only imported when load_model() is first called)

_LOCK = threading.Lock()          # generation-level mutex
_GENERATION_LOCK = threading.Lock()  # prevents concurrent generations


class CogVideoXService:
    """Local CogVideoX-2B text-to-video generation service."""

    def __init__(self):
        self.pipe = None
        self.is_loaded = False
        self._is_generating = False

    # ──────────────────────────────────────────────────────────────────────
    # Device detection
    # ──────────────────────────────────────────────────────────────────────
    def get_device_info(self) -> Dict[str, Any]:
        """Return hardware/memory status without loading the model."""
        cuda_ok = torch.cuda.is_available()
        info: Dict[str, Any] = {
            "model_id": settings.cogvideo_model_id,
            "available": True,
            "loaded": self.is_loaded,
            "is_generating": self._is_generating,
            "cuda_available": cuda_ok,
            "device": "cuda" if cuda_ok else "cpu",
            "gpu_name": None,
            "vram_total_gb": None,
            "vram_allocated_gb": None,
            "vram_free_gb": None,
        }
        if cuda_ok:
            info["gpu_name"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            total = props.total_memory
            allocated = torch.cuda.memory_allocated(0)
            reserved = torch.cuda.memory_reserved(0)
            info["vram_total_gb"] = round(total / 1024**3, 2)
            info["vram_allocated_gb"] = round(allocated / 1024**3, 2)
            info["vram_reserved_gb"] = round(reserved / 1024**3, 2)
            info["vram_free_gb"] = round((total - reserved) / 1024**3, 2)
        return info

    # ──────────────────────────────────────────────────────────────────────
    # Load
    # ──────────────────────────────────────────────────────────────────────
    def load_model(self) -> None:
        """Lazily load CogVideoX-2B with memory-safe settings.

        HF cache is redirected to D: drive (171 GB free) to avoid filling C:.
        If model files are not yet cached locally, this will trigger a download.
        """
        if self.is_loaded and self.pipe is not None:
            return

        import os
        from diffusers import CogVideoXPipeline  # lazy import

        # Redirect HuggingFace cache to D: drive BEFORE any HF imports resolve paths
        hf_cache = str(settings.hf_cache_dir)
        hf_hub = str(settings.hf_cache_dir / "hub")
        os.makedirs(hf_hub, exist_ok=True)

        # Only override if not already set to avoid overriding user's custom HF_HOME
        os.environ.setdefault("HF_HOME", hf_cache)
        os.environ.setdefault("HUGGINGFACE_HUB_CACHE", hf_hub)
        os.environ.setdefault("TRANSFORMERS_CACHE", hf_hub)

        cuda_ok = torch.cuda.is_available()
        device = "cuda" if cuda_ok else "cpu"
        dtype = torch.float16 if cuda_ok else torch.float32

        model_id = settings.cogvideo_model_id
        logger.info(f"[CogVideoX] Loading {model_id} on {device} with dtype={dtype}...")
        logger.info(f"[CogVideoX] HF cache: {hf_hub}")

        t0 = time.time()
        try:
            # Try loading from the D: drive HF cache first
            self.pipe = CogVideoXPipeline.from_pretrained(
                model_id,
                torch_dtype=dtype,
                cache_dir=hf_hub,
            )
        except Exception as exc:
            logger.error(f"[CogVideoX] from_pretrained failed: {exc}")
            logger.error(
                "[CogVideoX] Model weights are not fully downloaded. "
                f"Run: python scripts/download_cogvideox.py"
            )
            raise RuntimeError(
                f"CogVideoX model not available locally. "
                f"Please run: python scripts/download_cogvideox.py\n"
                f"Original error: {exc}"
            ) from exc

        # ── Memory optimisations ──────────────────────────────────────────
        # Sequential CPU offload: one transformer layer on GPU at a time.
        # This MUST be called BEFORE any .to(device) calls.
        self.pipe.enable_sequential_cpu_offload()

        # VAE slicing and tiling: decode large latents without OOM.
        try:
            self.pipe.vae.enable_slicing()
            self.pipe.vae.enable_tiling()
        except AttributeError:
            logger.warning("[CogVideoX] VAE slicing/tiling not available — skipping.")

        self.is_loaded = True
        elapsed = time.time() - t0
        logger.info(f"[CogVideoX] Model loaded in {elapsed:.1f}s.")

    # ──────────────────────────────────────────────────────────────────────
    # Unload
    # ──────────────────────────────────────────────────────────────────────
    def unload_model(self) -> None:
        """Free CogVideoX from GPU/CPU memory."""
        if not self.is_loaded:
            return
        logger.info("[CogVideoX] Unloading model...")
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
        self.is_loaded = False
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        logger.info("[CogVideoX] Model unloaded and memory cleared.")

    # ──────────────────────────────────────────────────────────────────────
    # Generate
    # ──────────────────────────────────────────────────────────────────────
    def generate_video(
        self,
        prompt: str,
        output_path: Path,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        num_frames: Optional[int] = None,
        fps: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate a single video clip and save it as MP4.
        Returns a result dict with success, path, duration, and timing info.
        """
        if not _GENERATION_LOCK.acquire(blocking=False):
            return {
                "success": False,
                "error": "Video generation already in progress. Please wait.",
                "error_type": "BusyError",
            }

        self._is_generating = True
        t_start = time.time()

        try:
            # Resolve parameters (config defaults as fallback)
            steps = num_inference_steps or settings.cogvideo_num_inference_steps
            guidance = guidance_scale or settings.cogvideo_guidance_scale
            frames = num_frames or settings.cogvideo_num_frames
            _fps = fps or settings.cogvideo_fps
            _w = width or settings.cogvideo_width
            _h = height or settings.cogvideo_height

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Load model (lazy, no-op if already loaded)
            t_load = time.time()
            self.load_model()
            load_elapsed = time.time() - t_load

            logger.info(
                f"[CogVideoX] Generating {frames} frames @ {_fps} FPS "
                f"({_w}x{_h}), steps={steps}, guidance={guidance}"
            )
            logger.info(f"[CogVideoX] Prompt: {prompt[:80]}...")

            t_gen = time.time()
            try:
                output = self.pipe(
                    prompt=prompt,
                    num_videos_per_prompt=1,
                    num_inference_steps=steps,
                    num_frames=frames,
                    guidance_scale=guidance,
                    generator=torch.Generator().manual_seed(42),
                    height=_h,
                    width=_w,
                )
            except torch.cuda.OutOfMemoryError as oom:
                # Report exact CUDA memory state and stop
                dev_info = self.get_device_info()
                self.unload_model()
                return {
                    "success": False,
                    "error": (
                        f"CUDA out of memory. "
                        f"VRAM total: {dev_info.get('vram_total_gb')} GB, "
                        f"allocated: {dev_info.get('vram_allocated_gb')} GB, "
                        f"free: {dev_info.get('vram_free_gb')} GB. "
                        f"Detail: {str(oom)}"
                    ),
                    "error_type": "CUDAOutOfMemory",
                    "device_info": dev_info,
                }
            gen_elapsed = time.time() - t_gen

            # Export frames to MP4
            from diffusers.utils import export_to_video
            frames_list = output.frames[0]
            export_to_video(frames_list, str(output_path), fps=_fps)

            total_elapsed = time.time() - t_start
            file_size = output_path.stat().st_size if output_path.exists() else 0
            video_duration = frames / _fps

            logger.info(
                f"[CogVideoX] Done — {output_path.name} "
                f"({file_size / 1024:.1f} KB, {video_duration:.1f}s) "
                f"in {total_elapsed:.1f}s total."
            )

            return {
                "success": True,
                "video_path": str(output_path),
                "duration": round(video_duration, 2),
                "fps": _fps,
                "frames": frames,
                "width": _w,
                "height": _h,
                "model_load_time": round(load_elapsed, 2),
                "generation_time": round(gen_elapsed, 2),
                "total_time": round(total_elapsed, 2),
                "file_size_bytes": file_size,
            }

        except Exception as exc:
            logger.error(f"[CogVideoX] Generation failed: {exc}", exc_info=True)
            return {
                "success": False,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
        finally:
            self._is_generating = False
            _GENERATION_LOCK.release()
            # Always unload after generation to free memory for Piper (Task 4)
            self.unload_model()


# Module-level singleton
cogvideo_service = CogVideoXService()
