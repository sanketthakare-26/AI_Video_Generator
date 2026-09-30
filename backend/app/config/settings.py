from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and configuration."""
    
    app_name: str = "AI Video Generator Backend"
    version: str = "0.1.0"
    api_prefix: str = "/api"
    debug: bool = False
    
    # CORS Origins (Frontend connection)
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    # Paths configuration
    base_dir: Path = Path(__file__).resolve().parent.parent.parent.parent
    models_dir: Path = base_dir / "models"
    generated_dir: Path = base_dir / "generated"
    # HuggingFace cache — keep on D: (171 GB free) not C: (11.7 GB free)
    hf_cache_dir: Path = base_dir / "models" / "hf_cache"

    # ── CogVideoX-2B settings ──────────────────────────────────────────────
    cogvideo_model_id: str = "THUDM/CogVideoX-2b"
    cogvideo_num_inference_steps: int = 10  # 10 steps on CPU (~1-2h per scene); increase once CUDA works
    cogvideo_guidance_scale: float = 6.0
    cogvideo_fps: int = 8
    cogvideo_width: int = 720
    cogvideo_height: int = 480
    cogvideo_num_frames: int = 49
    cogvideo_device: str = "cuda"   # auto-falls-back to cpu at runtime if CUDA unavailable

    # ── Piper TTS settings ────────────────────────────────────────────────
    piper_model_path: str = "models/piper/en_US-lessac-medium.onnx"
    piper_sample_rate: int = 22050
    piper_length_scale: float = 1.0
    piper_noise_scale: float = 0.667
    piper_noise_w_scale: float = 0.8

    # ── FFmpeg assembly settings ──────────────────────────────────────────
    ffmpeg_timeout_seconds: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )



settings = Settings()
