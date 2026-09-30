import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas.tts_generation import TTSGenerateRequest, TTSGenerateResponse
from app.services.tts_service import tts_service
from app.config.settings import settings
from app.utils.logger import logger

router = APIRouter()

PIPER_AUDIO_DIR = settings.generated_dir / "audio" / "piper"
PIPER_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "/generate-audio",
    response_model=TTSGenerateResponse,
    summary="Generate speech from text using local Piper TTS"
)
async def generate_audio(request: TTSGenerateRequest):
    """
    Accepts text and generates a WAV speech file using local Piper neural TTS.
    Runs locally on CPU with zero cloud API dependencies.
    """
    logger.info(f"[TTSEndpoint] Received TTS request: '{request.text[:50]}...'")

    # Resolve filename
    if request.filename:
        filename = request.filename if request.filename.endswith(".wav") else f"{request.filename}.wav"
    else:
        filename = "test_voice.wav"

    output_path = PIPER_AUDIO_DIR / filename

    # Run blocking ONNX synthesis in thread pool so FastAPI remains non-blocking
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: tts_service.generate_audio(
            text=request.text,
            output_path=output_path,
            language=request.language or "en",
        )
    )

    return TTSGenerateResponse(**result)


@router.get(
    "/audio/{filename}",
    summary="Serve generated WAV audio file for browser playback"
)
async def serve_audio(filename: str):
    """Serve synthesized WAV audio file to the frontend audio player."""
    audio_path = PIPER_AUDIO_DIR / filename
    if not audio_path.exists() or not audio_path.is_file():
        raise HTTPException(status_code=404, detail=f"Audio file '{filename}' not found.")
    return FileResponse(str(audio_path), media_type="audio/wav")


@router.post(
    "/unload-piper",
    summary="Unload Piper TTS voice model to free memory"
)
async def unload_piper():
    """Manually unload Piper model from memory."""
    tts_service.unload_model()
    return {
        "status": "success",
        "message": "Piper TTS model unloaded.",
        "device_info": tts_service.get_device_info(),
    }


@router.get(
    "/piper-status",
    summary="Check Piper TTS service status"
)
async def piper_status():
    """Returns Piper service status and model paths without loading the model."""
    return tts_service.get_device_info()
