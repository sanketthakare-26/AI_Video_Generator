from fastapi import APIRouter
from app.api.endpoints import health, generate, video_generate, tts_generate, assembly

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(generate.router, tags=["Generation (Qwen LLM)"])
api_router.include_router(video_generate.router, tags=["Video Generation (CogVideoX)"])
api_router.include_router(tts_generate.router, tags=["Voice Generation (Piper TTS)"])
api_router.include_router(assembly.router, tags=["Assembly & Full Pipeline (FFmpeg)"])


