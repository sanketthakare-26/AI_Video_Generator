from typing import List, Optional
from pydantic import BaseModel, Field


class AssembleVideoRequest(BaseModel):
    """Request body for POST /api/assemble-video."""
    video_files: List[str] = Field(..., min_length=1, description="List of video clip filenames to concatenate")
    audio_file: Optional[str] = Field(default=None, description="Audio filename (e.g. test_voice.wav)")
    voiceover_text: Optional[str] = Field(default=None, description="Narration text for subtitle generation")
    burn_subtitles: Optional[bool] = Field(default=False, description="Whether to hardcode/burn subtitles into video frames")
    output_filename: Optional[str] = Field(default=None, description="Optional custom output filename")


class AssembleVideoResponse(BaseModel):
    """Response from POST /api/assemble-video."""
    success: bool
    video_url: Optional[str] = None
    video_path: Optional[str] = None
    filename: Optional[str] = None
    duration: Optional[float] = None
    size_bytes: Optional[int] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    resolution: Optional[str] = None
    fps: Optional[float] = None
    has_audio: Optional[bool] = None
    has_subtitles: Optional[bool] = None
    srt_path: Optional[str] = None
    assembly_time: Optional[float] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


class FullPipelineRequest(BaseModel):
    """Request body for POST /api/generate-full-video."""
    prompt: str = Field(..., min_length=5, description="High-level text prompt for the entire video")
    duration: Optional[int] = Field(default=10, description="Target duration in seconds (e.g. 10, 15)")
    aspect_ratio: Optional[str] = Field(default="16:9", description="Video aspect ratio")
    language: Optional[str] = Field(default="English", description="Narration language")
    burn_subtitles: Optional[bool] = Field(default=False, description="Whether to burn subtitles")


class FullPipelineResponse(BaseModel):
    """Response from POST /api/generate-full-video."""
    success: bool
    video_url: Optional[str] = None
    video_path: Optional[str] = None
    filename: Optional[str] = None
    duration: Optional[float] = None
    title: Optional[str] = None
    scene_count: Optional[int] = None
    plan: Optional[dict] = None
    total_time: Optional[float] = None
    stages_completed: Optional[List[str]] = None
    audio_url: Optional[str] = None
    srt_path: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
