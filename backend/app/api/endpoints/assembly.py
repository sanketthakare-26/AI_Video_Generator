import asyncio
import gc
import time
from pathlib import Path
from typing import List, Optional

import torch
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas.assembly import (
    AssembleVideoRequest,
    AssembleVideoResponse,
    FullPipelineRequest,
    FullPipelineResponse,
)
from app.services.video_assembly_service import video_assembly_service
from app.services.pipeline_service import pipeline_service
from app.services.llm_service import llm_service
from app.services.video_service import cogvideo_service
from app.services.tts_service import tts_service
from app.config.settings import settings
from app.utils.logger import logger

router = APIRouter()

FINAL_VIDEO_DIR = settings.generated_dir / "videos" / "final"
FINAL_VIDEO_DIR.mkdir(parents=True, exist_ok=True)


@router.get(
    "/pipeline-status",
    summary="Get real-time status and active stage of full pipeline execution"
)
async def get_pipeline_status():
    """Returns current active pipeline stage, progress message, and completion status."""
    return pipeline_service.get_status()


@router.post(
    "/assemble-video",
    response_model=AssembleVideoResponse,
    summary="Assemble video clips, voice audio, and subtitles into final MP4 with FFmpeg"
)
async def assemble_video(request: AssembleVideoRequest):
    """
    Combines individual scene video clips with Piper voiceover audio and generates
    SRT subtitles using FFmpeg with strict timeout and verification.
    Runs in a worker thread so the FastAPI event loop stays responsive.
    """
    logger.info(f"[AssemblyEndpoint] Assembling {len(request.video_files)} video clips...")

    # Resolve video paths
    video_paths: List[Path] = []
    for vf in request.video_files:
        p = Path(vf)
        if not p.is_absolute():
            cand1 = settings.generated_dir / "videos" / "cogvideox" / vf
            cand2 = settings.generated_dir / "videos" / vf
            p = cand1 if cand1.exists() else cand2
        video_paths.append(p)

    # Resolve audio path
    audio_path: Optional[Path] = None
    if request.audio_file:
        ap = Path(request.audio_file)
        if not ap.is_absolute():
            cand1 = settings.generated_dir / "audio" / "piper" / request.audio_file
            cand2 = settings.generated_dir / "audio" / request.audio_file
            ap = cand1 if cand1.exists() else cand2
        audio_path = ap

    # Output file
    out_name = request.output_filename or f"ai_video_{int(time.time())}.mp4"
    if not out_name.endswith(".mp4"):
        out_name += ".mp4"
    output_path = FINAL_VIDEO_DIR / out_name

    result = await asyncio.to_thread(
        video_assembly_service.assemble_video,
        video_files=video_paths,
        audio_file=audio_path,
        output_mp4=output_path,
        voiceover_text=request.voiceover_text,
        burn_subtitles=bool(request.burn_subtitles),
        shortest=True,
    )

    return AssembleVideoResponse(**result)


@router.get(
    "/final-video/{filename}",
    summary="Serve final assembled MP4 video"
)
async def serve_final_video(filename: str):
    """Serve assembled final MP4 video for HTML5 browser streaming and downloading."""
    video_path = FINAL_VIDEO_DIR / filename
    if not video_path.exists() or not video_path.is_file():
        raise HTTPException(status_code=404, detail=f"Final video '{filename}' not found.")
    return FileResponse(str(video_path), media_type="video/mp4")


@router.get(
    "/assembly-status",
    summary="Check FFmpeg and FFprobe installation and version"
)
async def assembly_status():
    """Returns FFmpeg and FFprobe binary detection status."""
    return video_assembly_service.get_version()


def _execute_full_pipeline_sync(request: FullPipelineRequest) -> dict:
    """
    Synchronous orchestrator for full AI video pipeline.
    Runs in a background thread so the FastAPI event loop remains completely responsive
    for /api/health and /api/pipeline-status.
    """
    t_start = time.time()
    stages_completed: List[str] = []
    logger.info(f"[FullPipeline] Starting end-to-end generation: '{request.prompt[:60]}...'")

    pipeline_service.start_pipeline(request.prompt)

    try:
        # ── Stage 1: Qwen LLM Video Plan ──────────────────────────────────
        pipeline_service.update_stage(
            0,
            "1. Understanding Prompt",
            progress_message="Analyzing prompt with Qwen2.5-1.5B..."
        )
        logger.info("[FullPipeline] Stage 1: Generating VideoPlan with Qwen...")
        from app.schemas.generation import GenerateRequest
        gen_req = GenerateRequest(
            prompt=request.prompt,
            duration=request.duration or 15,
            aspect_ratio=request.aspect_ratio or "16:9",
            language=request.language or "English",
        )

        pipeline_service.update_stage(
            1,
            "2. Creating Script",
            completed_prev_stage="1. Understanding Prompt",
            progress_message="Generating storyline and narration script..."
        )

        plan = llm_service.generate_plan(gen_req)

        pipeline_service.update_stage(
            2,
            "3. Planning Scenes",
            completed_prev_stage="2. Creating Script",
            progress_message="Structuring scene prompts for video generation..."
        )
        stages_completed.append("Understanding Prompt & Planning Scenes (Qwen)")
        pipeline_service.complete_stage("3. Planning Scenes")

        # Unload Qwen to free RAM/VRAM before video generation
        llm_service.unload_model()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # ── Stage 2: CogVideoX Video Generation (Sequential) ──────────────
        scenes = plan.scenes
        if not scenes:
            raise ValueError("Qwen VideoPlan produced 0 scenes.")

        total_scenes = len(scenes)
        logger.info(f"[FullPipeline] Video plan contains {total_scenes} scenes for {gen_req.duration}s requested duration.")

        video_clip_paths: List[Path] = []
        clip_dir = settings.generated_dir / "videos" / "cogvideox"
        clip_dir.mkdir(parents=True, exist_ok=True)

        for i, scene in enumerate(scenes):
            scene_num = scene.scene_number or (i + 1)
            stage_idx = 3 + min(i, 2)
            stage_label = f"Generating Scene {scene_num}"
            prev_label = f"Generating Scene {scene_num - 1}" if i > 0 else "3. Planning Scenes"

            pipeline_service.update_stage(
                stage_idx,
                stage_label,
                completed_prev_stage=prev_label,
                progress_message=f"Rendering Scene {scene_num}/{total_scenes} ({scene.duration}s) with CogVideoX-2B..."
            )

            clip_path = clip_dir / f"scene_{scene_num:03d}_{int(time.time() * 1000)}.mp4"
            logger.info(f"[FullPipeline] Stage 2.{scene_num}: Generating video for Scene {scene_num}/{total_scenes} -> {clip_path.name}")

            v_res = cogvideo_service.generate_video(
                prompt=scene.video_prompt,
                output_path=clip_path,
                num_inference_steps=settings.cogvideo_num_inference_steps,
                guidance_scale=settings.cogvideo_guidance_scale,
                num_frames=settings.cogvideo_num_frames,
                fps=settings.cogvideo_fps,
                width=settings.cogvideo_width,
                height=settings.cogvideo_height,
            )
            if not v_res.get("success"):
                raise RuntimeError(f"Video generation failed for Scene {scene_num}: {v_res.get('error')}")

            if not clip_path.exists() or clip_path.stat().st_size == 0:
                raise RuntimeError(f"Scene {scene_num} video file not found or empty at {clip_path}")

            video_clip_paths.append(clip_path)
            stage_done_text = f"Generated Scene {scene_num} Video Clip (CogVideoX)"
            stages_completed.append(stage_done_text)
            pipeline_service.complete_stage(stage_label)

        # Verification of scene count before moving on
        if len(video_clip_paths) != len(scenes):
            raise RuntimeError(
                f"Scene count mismatch: Expected {len(scenes)} clips, but only {len(video_clip_paths)} were generated."
            )

        # Unload CogVideoX before TTS
        cogvideo_service.unload_model()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # ── Stage 3: Piper TTS Narration ──────────────────────────────────
        pipeline_service.update_stage(
            5,
            "6. Generating Voice",
            completed_prev_stage=f"Generating Scene {total_scenes}",
            progress_message="Synthesizing neural speech with Piper TTS on CPU..."
        )
        logger.info("[FullPipeline] Stage 3: Generating voiceover with Piper TTS...")
        audio_dir = settings.generated_dir / "audio" / "piper"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / f"voiceover_{int(time.time() * 1000)}.wav"

        tts_res = tts_service.generate_audio(
            text=plan.voiceover,
            output_path=audio_path,
            language="en",
        )
        if not tts_res.get("success"):
            raise RuntimeError(f"Voice generation failed: {tts_res.get('error')}")

        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise RuntimeError(f"Voiceover audio file not found or empty at {audio_path}")

        stages_completed.append("Synthesized Voice Narration (Piper TTS)")
        pipeline_service.complete_stage("6. Generating Voice")

        # Unload Piper
        tts_service.unload_model()
        gc.collect()

        # ── Stage 4: FFmpeg Final Assembly ────────────────────────────────
        pipeline_service.update_stage(
            6,
            "7. Creating Subtitles",
            completed_prev_stage="6. Generating Voice",
            progress_message="Parsing narration timestamps and generating SRT..."
        )
        pipeline_service.complete_stage("7. Creating Subtitles")

        pipeline_service.update_stage(
            7,
            "8. Assembling Final Video",
            completed_prev_stage="7. Creating Subtitles",
            progress_message="Assembling video clips, audio, and subtitles with FFmpeg..."
        )
        logger.info("[FullPipeline] Stage 4: Assembling final MP4 with FFmpeg...")
        final_filename = f"ai_video_{int(time.time())}.mp4"
        final_mp4_path = FINAL_VIDEO_DIR / final_filename

        assembly_res = video_assembly_service.assemble_video(
            video_files=video_clip_paths,
            audio_file=audio_path,
            output_mp4=final_mp4_path,
            voiceover_text=plan.voiceover,
            burn_subtitles=bool(request.burn_subtitles),
            shortest=True,
        )
        if not assembly_res.get("success"):
            raise RuntimeError(f"FFmpeg assembly failed: {assembly_res.get('error')}")

        stages_completed.append("Created Subtitles & Assembled Final MP4 (FFmpeg)")
        pipeline_service.complete_stage("8. Assembling Final Video")

        total_elapsed = time.time() - t_start
        logger.info(f"[FullPipeline] Pipeline completed successfully in {total_elapsed:.1f}s: {final_filename}")

        resp_data = {
            "success": True,
            "video_url": f"/api/final-video/{final_filename}",
            "video_path": str(final_mp4_path),
            "filename": final_filename,
            "duration": assembly_res.get("duration"),
            "title": plan.title,
            "scene_count": len(scenes),
            "plan": plan.model_dump(),
            "total_time": round(total_elapsed, 2),
            "stages_completed": stages_completed,
            "audio_url": f"/api/audio/{audio_path.name}",
            "srt_path": assembly_res.get("srt_path"),
        }

        pipeline_service.set_success(resp_data)
        return resp_data

    except Exception as exc:
        logger.error(f"[FullPipeline] Pipeline execution failed: {exc}", exc_info=True)
        pipeline_service.set_error(str(exc), error_type=type(exc).__name__)
        return {
            "success": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "stages_completed": stages_completed,
        }


@router.post(
    "/generate-full-video",
    response_model=FullPipelineResponse,
    summary="End-to-End Orchestration: Prompt -> Qwen -> CogVideoX -> Piper -> FFmpeg -> Final MP4"
)
async def generate_full_video(request: FullPipelineRequest):
    """
    Executes the full sequential AI video generation pipeline asynchronously via thread pool:
    1. Qwen LLM creates structured VideoPlan
    2. Qwen unloads to free memory
    3. CogVideoX generates video clip for each scene sequentially
    4. CogVideoX unloads to free memory
    5. Piper TTS generates voiceover audio from narration script
    6. Piper unloads to free memory
    7. FFmpeg joins clips, adds voiceover, generates subtitles, and encodes final MP4
    """
    resp_dict = await asyncio.to_thread(_execute_full_pipeline_sync, request)
    return FullPipelineResponse(**resp_dict)
