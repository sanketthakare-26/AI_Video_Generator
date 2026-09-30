from typing import Optional
from pydantic import BaseModel, Field


class TTSGenerateRequest(BaseModel):
    """Request body for POST /api/generate-audio."""
    text: str = Field(..., min_length=1, description="Text to synthesize into spoken narration")
    language: Optional[str] = Field(default="en", description="Target language code (en)")
    filename: Optional[str] = Field(default=None, description="Optional custom output filename without path")


class TTSGenerateResponse(BaseModel):
    """Response from POST /api/generate-audio."""
    success: bool
    audio_path: Optional[str] = None
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    sample_width: Optional[int] = None
    frames: Optional[int] = None
    file_size_bytes: Optional[int] = None
    model_load_time: Optional[float] = None
    generation_time: Optional[float] = None
    total_time: Optional[float] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
