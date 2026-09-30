"""Video Generation Pipeline Coordinator & Real-time Progress Tracking.

Sequential execution design for 4GB VRAM GPU:
Stage 1: Understanding Prompt & Planning Scenes (Qwen LLM) -> Unload LLM
Stage 2: Generating Video Clips (CogVideoX) -> Unload CogVideoX
Stage 3: Generating Voice Narration (Piper TTS) -> Unload TTS
Stage 4: Combining Video, Audio & Subtitles (FFmpeg)
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.utils.logger import logger


class PipelineStatusModel(BaseModel):
    is_running: bool = False
    current_stage_index: int = -1
    current_stage_name: str = "Standby"
    total_stages: int = 9
    stages_completed: List[str] = Field(default_factory=list)
    progress_message: str = "Ready"
    error: Optional[str] = None
    error_type: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    timestamp: float = Field(default_factory=time.time)


class PipelineService:
    """Manages real-time stage progress and state tracking for the full video pipeline."""

    def __init__(self):
        self._lock = threading.Lock()
        self._status = PipelineStatusModel()

    def start_pipeline(self, prompt: str, total_stages: int = 9) -> None:
        """Initialize pipeline state when a new generation run starts."""
        with self._lock:
            self._status = PipelineStatusModel(
                is_running=True,
                current_stage_index=0,
                current_stage_name="1. Understanding Prompt",
                total_stages=total_stages,
                stages_completed=[],
                progress_message=f"Starting generation for: '{prompt[:50]}...'",
                error=None,
                error_type=None,
                result=None,
                timestamp=time.time(),
            )
            logger.info(f"[PipelineService] Pipeline started: '{prompt[:50]}'")

    def update_stage(
        self,
        stage_index: int,
        stage_name: str,
        completed_prev_stage: Optional[str] = None,
        progress_message: Optional[str] = None
    ) -> None:
        """Update current active stage and record completed stage."""
        with self._lock:
            if completed_prev_stage and completed_prev_stage not in self._status.stages_completed:
                self._status.stages_completed.append(completed_prev_stage)
            self._status.current_stage_index = stage_index
            self._status.current_stage_name = stage_name
            if progress_message:
                self._status.progress_message = progress_message
            self._status.timestamp = time.time()
            logger.info(f"[PipelineService] Active Stage [{stage_index}]: {stage_name}")

    def complete_stage(self, stage_label: str) -> None:
        """Mark a specific stage as completed."""
        with self._lock:
            if stage_label not in self._status.stages_completed:
                self._status.stages_completed.append(stage_label)
            self._status.timestamp = time.time()

    def set_error(self, error_message: str, error_type: str = "PipelineError") -> None:
        """Record pipeline failure."""
        with self._lock:
            self._status.is_running = False
            self._status.error = error_message
            self._status.error_type = error_type
            self._status.progress_message = f"Failed: {error_message}"
            self._status.timestamp = time.time()
            logger.error(f"[PipelineService] Pipeline failed: {error_message}")

    def set_success(self, result_data: Dict[str, Any]) -> None:
        """Record pipeline completion."""
        with self._lock:
            self._status.is_running = False
            self._status.current_stage_index = 8
            self._status.current_stage_name = "Completed"
            if "Completed" not in self._status.stages_completed:
                self._status.stages_completed.append("Completed")
            self._status.progress_message = "Video generated successfully!"
            self._status.result = result_data
            self._status.timestamp = time.time()
            logger.info("[PipelineService] Pipeline completed successfully.")

    def get_status(self) -> Dict[str, Any]:
        """Return current snapshot of pipeline execution."""
        with self._lock:
            return self._status.model_dump()


pipeline_service = PipelineService()
