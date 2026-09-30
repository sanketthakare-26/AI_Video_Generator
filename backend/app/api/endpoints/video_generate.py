import asyncio
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import FileResponse

from app.schemas.video_generation import VideoGenerateRequest, VideoGenerateResponse
from app.services.video_service import cogvideo_service
from app.config.settings import settings
from app.utils.logger import logger

router = APIRouter()

# Output directory for CogVideoX clips
COGVIDEO_OUTPUT_DIR = settings.generated_dir / "videos" / "cogvideox"
COGVIDEO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "/generate-video",
    response_model=VideoGenerateResponse,
    summary="Generate a short video clip using CogVideoX-2B (local, no cloud API)"
)
async def generate_video(request: VideoGenerateRequest):
    """
    Accepts a text prompt and runs CogVideoX-2B locally to produce an MP4 clip.
    Uses sequential CPU offload + VAE slicing for 4 GB VRAM hardware.
    Only one generation can run at a time.
    """
    logger.info(f"[VideoEndpoint] Received video request: {request.prompt[:60]}...")

    output_file = COGVIDEO_OUTPUT_DIR / "cogvideox_test.mp4"

    # Run blocking generation in thread pool so FastAPI stays responsive
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: cogvideo_service.generate_video(
            prompt=request.prompt,
            output_path=output_file,
        )
    )

    if result["success"]:
        # Add a URL path the frontend can use to stream/play the file
        result["video_url"] = f"/api/video/cogvideox_test.mp4"

    return VideoGenerateResponse(**result)


@router.get(
    "/video/{filename}",
    summary="Serve generated video file for frontend playback"
)
async def serve_video(filename: str):
    """Serve a generated video file to the frontend video player."""
    video_path = COGVIDEO_OUTPUT_DIR / filename
    if not video_path.exists() or not video_path.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Video '{filename}' not found.")
    return FileResponse(str(video_path), media_type="video/mp4")


@router.post(
    "/unload-cogvideo",
    summary="Unload CogVideoX from memory to free VRAM for next pipeline stage"
)
async def unload_cogvideo():
    """Manually unload CogVideoX model to reclaim VRAM before loading Piper TTS."""
    cogvideo_service.unload_model()
    return {
        "status": "success",
        "message": "CogVideoX model unloaded.",
        "device_info": cogvideo_service.get_device_info()
    }


@router.get(
    "/cogvideo-status",
    summary="Get CogVideoX service status without loading the model"
)
async def cogvideo_status():
    """Returns CogVideoX hardware/memory status. Does NOT load the model."""
    return cogvideo_service.get_device_info()
