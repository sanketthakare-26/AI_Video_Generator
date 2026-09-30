"""
Video Assembly Service using FFmpeg & FFprobe.

Handles:
  - Video clip concatenation (concat demuxer with re-encode fallback)
  - Adding synthesized Piper voiceover audio
  - SRT subtitle generation & optional burning
  - Safe subprocess execution with configurable timeout (FFMPEG_TIMEOUT_SECONDS = 300)
  - H.264 / AAC / MP4 encoding with yuv420p pixel format
  - Detailed pipeline logging and pre-assembly file verification
  - Automatic temporary file cleanup
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.utils.logger import logger


class VideoAssemblyService:
    """Service for combining video clips, voiceover audio, and subtitles via FFmpeg."""

    def __init__(self):
        self._ffmpeg_bin: Optional[str] = None
        self._ffprobe_bin: Optional[str] = None
        self.default_timeout: int = getattr(settings, "ffmpeg_timeout_seconds", 300)

    # ──────────────────────────────────────────────────────────────────────
    # Binary Discovery
    # ──────────────────────────────────────────────────────────────────────
    def get_ffmpeg_path(self) -> str:
        """Resolve path to ffmpeg executable."""
        if self._ffmpeg_bin and Path(self._ffmpeg_bin).exists():
            return self._ffmpeg_bin

        # 1. Check tools/ffmpeg/bin
        local_tool = settings.base_dir / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
        if local_tool.exists():
            self._ffmpeg_bin = str(local_tool)
            return self._ffmpeg_bin

        # 2. Check system PATH
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            self._ffmpeg_bin = system_ffmpeg
            return self._ffmpeg_bin

        # 3. Check imageio_ffmpeg bundled binary as fallback
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if exe and Path(exe).exists():
                self._ffmpeg_bin = exe
                return self._ffmpeg_bin
        except Exception:
            pass

        raise FileNotFoundError(
            "FFmpeg executable not found. Run 'python scripts/setup_ffmpeg.py' to download FFmpeg."
        )

    def get_ffprobe_path(self) -> str:
        """Resolve path to ffprobe executable."""
        if self._ffprobe_bin and Path(self._ffprobe_bin).exists():
            return self._ffprobe_bin

        # 1. Check tools/ffmpeg/bin
        local_tool = settings.base_dir / "tools" / "ffmpeg" / "bin" / "ffprobe.exe"
        if local_tool.exists():
            self._ffprobe_bin = str(local_tool)
            return self._ffprobe_bin

        # 2. Check system PATH
        system_ffprobe = shutil.which("ffprobe")
        if system_ffprobe:
            self._ffprobe_bin = system_ffprobe
            return self._ffprobe_bin

        raise FileNotFoundError(
            "FFprobe executable not found. Run 'python scripts/setup_ffmpeg.py' to download FFprobe."
        )

    def is_available(self) -> bool:
        """Check if FFmpeg and FFprobe are available."""
        try:
            self.get_ffmpeg_path()
            return True
        except FileNotFoundError:
            return False

    def get_version(self) -> Dict[str, Any]:
        """Get version strings for FFmpeg and FFprobe without failing, using cached discovery."""
        if hasattr(self, "_cached_version") and self._cached_version and self._cached_version.get("available"):
            return self._cached_version

        info = {
            "available": False,
            "ffmpeg_path": None,
            "ffprobe_path": None,
            "ffmpeg_version": None,
            "ffprobe_version": None,
        }
        try:
            ffmpeg_exe = self.get_ffmpeg_path()
            info["ffmpeg_path"] = ffmpeg_exe
            res = subprocess.run(
                [ffmpeg_exe, "-version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if res.returncode == 0:
                first_line = res.stdout.splitlines()[0] if res.stdout else "unknown"
                info["ffmpeg_version"] = first_line
                info["available"] = True
        except Exception as exc:
            info["error_ffmpeg"] = str(exc)

        try:
            ffprobe_exe = self.get_ffprobe_path()
            info["ffprobe_path"] = ffprobe_exe
            res_probe = subprocess.run(
                [ffprobe_exe, "-version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if res_probe.returncode == 0:
                first_line = res_probe.stdout.splitlines()[0] if res_probe.stdout else "unknown"
                info["ffprobe_version"] = first_line
        except Exception as exc:
            info["error_ffprobe"] = str(exc)

        self._cached_version = info
        return info

    # ──────────────────────────────────────────────────────────────────────
    # Robust Subprocess Execution
    # ──────────────────────────────────────────────────────────────────────
    def _run_ffmpeg_command(
        self,
        cmd: List[str],
        timeout: Optional[int] = None,
        step_name: str = "FFmpeg Execution"
    ) -> subprocess.CompletedProcess:
        """
        Execute an FFmpeg command with guaranteed timeout, stdout/stderr capture,
        and detailed logging. Never hangs indefinitely.
        """
        actual_timeout = timeout or self.default_timeout
        cmd_str = " ".join(cmd)
        logger.info(f"FFmpeg started: {step_name}...")
        logger.info(f"FFmpeg command: {cmd_str}")

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=actual_timeout,
                check=False
            )
        except subprocess.TimeoutExpired as exc:
            logger.error(
                f"FFmpeg timed out after {actual_timeout} seconds during '{step_name}'. Process terminated."
            )
            raise TimeoutError(
                f"FFmpeg timed out after {actual_timeout} seconds during '{step_name}'. Process terminated."
            ) from exc
        except Exception as exc:
            logger.error(f"FFmpeg execution failed to start: {exc}")
            raise

        if res.returncode == 0:
            logger.info(f"FFmpeg completed with return code 0 ({step_name})")
            return res
        else:
            stderr_snippet = res.stderr.strip() if res.stderr else "Unknown error"
            logger.error(
                f"FFmpeg failed with return code {res.returncode} ({step_name})\n"
                f"FFmpeg stderr:\n{stderr_snippet}"
            )
            raise RuntimeError(
                f"FFmpeg ({step_name}) failed with return code {res.returncode}:\n{stderr_snippet}"
            )

    # ──────────────────────────────────────────────────────────────────────
    # Subtitles (SRT)
    # ──────────────────────────────────────────────────────────────────────
    @staticmethod
    def _format_srt_time(seconds: float) -> str:
        """Format seconds into SRT timestamp HH:MM:SS,mmm."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

    def create_subtitles(
        self,
        voiceover_text: str,
        total_duration: float,
        output_srt: Path
    ) -> Path:
        """
        Divide narration text into sentence chunks and write standard SRT file.
        """
        output_srt.parent.mkdir(parents=True, exist_ok=True)
        raw_sentences = re.split(r'(?<=[.!?])\s+', (voiceover_text or "").strip())
        sentences = [s.strip() for s in raw_sentences if s.strip()]

        if not sentences:
            sentences = [voiceover_text.strip()] if (voiceover_text and voiceover_text.strip()) else ["AI Video Generation"]

        chunk_count = len(sentences)
        time_per_chunk = max(total_duration / chunk_count, 1.0)

        lines = []
        for i, sentence in enumerate(sentences):
            start_t = i * time_per_chunk
            end_t = min((i + 1) * time_per_chunk, total_duration)
            if start_t >= total_duration:
                break
            lines.append(str(i + 1))
            lines.append(f"{self._format_srt_time(start_t)} --> {self._format_srt_time(end_t)}")
            lines.append(sentence)
            lines.append("")

        output_srt.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"[Assembly] Generated SRT subtitles ({len(sentences)} chunks) at: {output_srt}")
        return output_srt

    # ──────────────────────────────────────────────────────────────────────
    # Concat File
    # ──────────────────────────────────────────────────────────────────────
    def create_concat_file(self, video_files: List[Path], concat_txt_path: Path) -> Path:
        """Write safe concat demuxer text file."""
        concat_txt_path.parent.mkdir(parents=True, exist_ok=True)
        content_lines = []
        for v in video_files:
            abs_str = str(v.resolve()).replace("\\", "/")
            content_lines.append(f"file '{abs_str}'")

        concat_txt_path.write_text("\n".join(content_lines), encoding="utf-8")
        logger.info(f"[Assembly] Created concat file ({len(video_files)} clips) at {concat_txt_path}")
        return concat_txt_path

    # ──────────────────────────────────────────────────────────────────────
    # FFprobe Inspection
    # ──────────────────────────────────────────────────────────────────────
    def inspect_video(self, media_path: Path) -> Dict[str, Any]:
        """Inspect media file using ffprobe and return structured metadata."""
        ffprobe_exe = self.get_ffprobe_path()
        cmd = [
            ffprobe_exe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(media_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"FFprobe inspection timed out for: {media_path}") from exc

        if result.returncode != 0:
            raise RuntimeError(f"FFprobe inspection failed: {result.stderr}")

        data = json.loads(result.stdout)
        fmt = data.get("format", {})
        streams = data.get("streams", [])

        v_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

        # Parse FPS
        fps = 0.0
        r_fps = v_stream.get("r_frame_rate", "0/1")
        try:
            num, den = map(int, r_fps.split("/"))
            fps = round(num / den, 2) if den > 0 else 0.0
        except Exception:
            pass

        return {
            "filename": media_path.name,
            "path": str(media_path),
            "size_bytes": int(fmt.get("size", 0)),
            "duration": float(fmt.get("duration", 0.0)),
            "video_codec": v_stream.get("codec_name"),
            "width": v_stream.get("width"),
            "height": v_stream.get("height"),
            "fps": fps,
            "has_video": bool(v_stream),
            "audio_codec": a_stream.get("codec_name"),
            "sample_rate": int(a_stream.get("sample_rate", 0)) if a_stream.get("sample_rate") else None,
            "channels": a_stream.get("channels"),
            "has_audio": bool(a_stream),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Video Assembly
    # ──────────────────────────────────────────────────────────────────────
    def assemble_video(
        self,
        video_files: List[Path],
        audio_file: Optional[Path],
        output_mp4: Path,
        voiceover_text: Optional[str] = None,
        burn_subtitles: bool = False,
        shortest: bool = True,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Join video clips, add audio, optionally burn subtitles, and encode to final MP4.
        """
        t_start = time.time()
        actual_timeout = timeout or self.default_timeout

        # Resolve binaries
        try:
            ffmpeg_exe = self.get_ffmpeg_path()
            self.get_ffprobe_path()
        except Exception as exc:
            return {
                "success": False,
                "error": f"FFmpeg/FFprobe binary resolution failed: {exc}",
                "error_type": type(exc).__name__,
            }

        # ── Step 2: Validate & Log All Input Files ─────────────────────────
        if not video_files:
            logger.error("[Assembly] No video clips provided for assembly.")
            return {
                "success": False,
                "error": "No video clips provided for assembly.",
                "error_type": "ValidationError",
            }

        # Check every scene file
        missing_scenes = []
        scene_meta_list = []
        for idx, vf in enumerate(video_files, start=1):
            if not vf.exists() or vf.stat().st_size == 0:
                missing_scenes.append(str(vf))
                scene_meta_list.append((idx, vf, False, 0.0))
            else:
                try:
                    meta = self.inspect_video(vf)
                    dur = meta.get("duration", 0.0)
                    scene_meta_list.append((idx, vf, True, dur))
                except Exception:
                    scene_meta_list.append((idx, vf, True, 0.0))

        # Check audio
        audio_exists = audio_file.exists() and audio_file.stat().st_size > 0 if audio_file else False
        audio_dur = 0.0
        if audio_exists and audio_file:
            try:
                ameta = self.inspect_video(audio_file)
                audio_dur = ameta.get("duration", 0.0)
            except Exception:
                pass

        # Prepare SRT path
        srt_path: Optional[Path] = None
        if voiceover_text and voiceover_text.strip():
            srt_filename = f"{output_mp4.stem}.srt"
            srt_path = settings.generated_dir / "subtitles" / srt_filename

        # Formatted verification log
        debug_lines = [
            "\n" + "=" * 60,
            "FULL PIPELINE DEBUG",
            "=" * 60,
            "Scenes:"
        ]
        for idx, vf, ex, dur in scene_meta_list:
            debug_lines.append(f"{idx}. {vf} exists={ex} duration={dur:.2f}s")
        debug_lines.append(f"\nAudio:\n{audio_file} exists={audio_exists} duration={audio_dur:.2f}s")
        debug_lines.append(f"\nSubtitle:\n{srt_path} planned_text_len={len(voiceover_text or '')}")
        debug_lines.append(f"\nFinal Output:\n{output_mp4}")
        debug_lines.append(f"\nFFmpeg:\n{ffmpeg_exe}")
        debug_lines.append("=" * 60)
        logger.info("\n".join(debug_lines))

        # Reject if any scene is missing
        if missing_scenes:
            err_msg = f"Cannot assemble video. Missing or empty scene file(s): {', '.join(missing_scenes)}"
            logger.error(f"[Assembly] {err_msg}")
            return {
                "success": False,
                "error": err_msg,
                "error_type": "FileNotFoundError",
            }

        temp_dir = settings.generated_dir / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_mp4.parent.mkdir(parents=True, exist_ok=True)

        temp_files_to_cleanup: List[Path] = []

        try:
            # ── 1. Concatenate Video Clips ────────────────────────────────
            if len(video_files) == 1:
                joined_video = video_files[0]
            else:
                concat_txt = temp_dir / f"concat_{int(time.time() * 1000)}.txt"
                self.create_concat_file(video_files, concat_txt)
                temp_files_to_cleanup.append(concat_txt)

                joined_video = temp_dir / f"joined_{int(time.time() * 1000)}.mp4"
                temp_files_to_cleanup.append(joined_video)

                concat_cmd = [
                    ffmpeg_exe,
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_txt),
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-crf", "23",
                    "-preset", "fast",
                    str(joined_video),
                ]
                self._run_ffmpeg_command(
                    concat_cmd,
                    timeout=actual_timeout,
                    step_name="Video Concatenation"
                )

            # ── 2. Create Subtitles (if voiceover text provided) ─────────
            if srt_path and voiceover_text:
                try:
                    meta = self.inspect_video(joined_video)
                    dur = meta.get("duration", 6.0)
                except Exception:
                    dur = sum(d for _, _, _, d in scene_meta_list) or 6.0

                self.create_subtitles(voiceover_text, dur, srt_path)

            # ── 3. Final Assembly: Video + Audio + Optional Subtitles ─────
            cmd = [ffmpeg_exe, "-y", "-i", str(joined_video)]

            has_audio = False
            if audio_file and audio_file.exists() and audio_file.stat().st_size > 0:
                has_audio = True
                cmd.extend(["-i", str(audio_file)])

            # Video encoding & filters
            filter_chains = []
            if burn_subtitles and srt_path and srt_path.exists():
                escaped_srt = str(srt_path.resolve()).replace("\\", "/").replace(":", "\\:")
                filter_chains.append(f"subtitles='{escaped_srt}'")

            if filter_chains:
                cmd.extend(["-vf", ",".join(filter_chains)])

            cmd.extend([
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "23",
                "-preset", "fast",
            ])

            if has_audio:
                cmd.extend([
                    "-c:a", "aac",
                    "-b:a", "128k",
                ])
                if shortest:
                    cmd.append("-shortest")
            else:
                cmd.extend(["-c:a", "copy"])

            cmd.append(str(output_mp4))

            try:
                self._run_ffmpeg_command(
                    cmd,
                    timeout=actual_timeout,
                    step_name="Final Assembly Encoding"
                )
            except RuntimeError as exc:
                # If burned subtitle assembly failed, fallback to clean assembly without burned subtitles
                if burn_subtitles:
                    logger.warning("[Assembly] Burned subtitles filter failed; falling back to clean assembly without subtitles...")
                    cmd_fallback = [ffmpeg_exe, "-y", "-i", str(joined_video)]
                    if has_audio:
                        cmd_fallback.extend(["-i", str(audio_file), "-c:a", "aac", "-b:a", "128k"])
                        if shortest:
                            cmd_fallback.append("-shortest")
                    cmd_fallback.extend([
                        "-c:v", "libx264",
                        "-pix_fmt", "yuv420p",
                        "-crf", "23",
                        "-preset", "fast",
                        str(output_mp4)
                    ])
                    self._run_ffmpeg_command(
                        cmd_fallback,
                        timeout=actual_timeout,
                        step_name="Final Assembly Fallback (No Burned Subtitles)"
                    )
                else:
                    raise

            # ── 4. Verify Final MP4 Output ────────────────────────────────
            if not output_mp4.exists() or output_mp4.stat().st_size == 0:
                raise RuntimeError("Final MP4 was not produced or is 0 bytes.")

            info = self.inspect_video(output_mp4)
            elapsed = time.time() - t_start
            logger.info(
                f"[Assembly] Final video successfully assembled in {elapsed:.2f}s: "
                f"{output_mp4.name} (Duration: {info.get('duration')}s, Size: {info.get('size_bytes')} bytes)"
            )

            return {
                "success": True,
                "video_path": str(output_mp4),
                "video_url": f"/api/final-video/{output_mp4.name}",
                "filename": output_mp4.name,
                "duration": info.get("duration"),
                "size_bytes": info.get("size_bytes"),
                "video_codec": info.get("video_codec"),
                "audio_codec": info.get("audio_codec"),
                "resolution": f"{info.get('width')}x{info.get('height')}",
                "fps": info.get("fps"),
                "has_audio": info.get("has_audio"),
                "has_subtitles": srt_path is not None and srt_path.exists(),
                "srt_path": str(srt_path) if srt_path else None,
                "assembly_time": round(elapsed, 2),
            }

        except Exception as exc:
            logger.error(f"[Assembly] Error during video assembly: {exc}", exc_info=True)
            return {
                "success": False,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
        finally:
            self.cleanup_temp_files(temp_files_to_cleanup)

    # ──────────────────────────────────────────────────────────────────────
    # Cleanup
    # ──────────────────────────────────────────────────────────────────────
    @staticmethod
    def cleanup_temp_files(temp_files: List[Path]) -> None:
        """Remove intermediate and temporary files."""
        for tf in temp_files:
            try:
                if tf and tf.exists():
                    tf.unlink()
                    logger.debug(f"[Assembly] Removed temporary file: {tf}")
            except Exception as e:
                logger.warning(f"[Assembly] Failed to clean up temp file {tf}: {e}")


# Singleton instance
video_assembly_service = VideoAssemblyService()
