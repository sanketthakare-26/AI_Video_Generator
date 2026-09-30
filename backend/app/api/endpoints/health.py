from fastapi import APIRouter
from app.schemas.generation import HealthResponse
from app.services.llm_service import llm_service
from app.services.video_service import cogvideo_service
from app.services.tts_service import tts_service
from app.services.video_assembly_service import video_assembly_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Health & Hardware Status Check")
async def health_check():
    """Returns backend service operational status, detected hardware, and model states."""
    device_info = llm_service.get_device_info()
    cogvideo_info = cogvideo_service.get_device_info()
    tts_info = tts_service.get_device_info()
    ffmpeg_info = video_assembly_service.get_version()

    return HealthResponse(
        status="ok",
        service="AI Video Generator Backend",
        device_info={
            **device_info,
            "cogvideo": {
                "available": True,
                "model_id": cogvideo_info.get("model_id"),
                "loaded": cogvideo_info.get("loaded"),
                "is_generating": cogvideo_info.get("is_generating"),
                "cuda_available": cogvideo_info.get("cuda_available"),
                "gpu_name": cogvideo_info.get("gpu_name"),
                "vram_total_gb": cogvideo_info.get("vram_total_gb"),
                "vram_free_gb": cogvideo_info.get("vram_free_gb"),
            },
            "piper": {
                "available": tts_info.get("available"),
                "loaded": tts_info.get("loaded"),
                "is_generating": tts_info.get("is_generating"),
                "model_path": tts_info.get("model_path"),
                "sample_rate": tts_info.get("sample_rate"),
                "device": tts_info.get("device"),
            },
            "ffmpeg": {
                "available": ffmpeg_info.get("available"),
                "version": ffmpeg_info.get("ffmpeg_version"),
                "ffprobe_version": ffmpeg_info.get("ffprobe_version"),
            }
        }
    )


