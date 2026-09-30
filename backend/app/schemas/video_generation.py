from typing import Optional
from pydantic import BaseModel, Field


class VideoGenerateRequest(BaseModel):
    """Request body for POST /api/generate-video."""
    prompt: str = Field(..., min_length=5, description="Video generation prompt (in English)")
    duration: Optional[int] = Field(default=6, description="Approximate target duration in seconds")
    aspect_ratio: Optional[str] = Field(default="16:9", description="Aspect ratio hint (16:9, 9:16, 1:1)")


class VideoGenerateResponse(BaseModel):
    """Response from POST /api/generate-video."""
    success: bool
    video_path: Optional[str] = None
    video_url: Optional[str] = None   # Served path for frontend player
    duration: Optional[float] = None
    fps: Optional[int] = None
    frames: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    model_load_time: Optional[float] = None
    generation_time: Optional[float] = None
    total_time: Optional[float] = None
    file_size_bytes: Optional[int] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    device_info: Optional[dict] = None
