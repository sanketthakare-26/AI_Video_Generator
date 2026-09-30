import asyncio
from fastapi import APIRouter, HTTPException, status
from app.schemas.generation import GenerateRequest, GenerateResponse
from app.services.llm_service import llm_service
from app.utils.logger import logger

router = APIRouter()


@router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Structured Video Plan via Qwen2.5-1.5B-Instruct"
)
async def generate_video_plan(request: GenerateRequest):
    """
    Executes local Qwen2.5-1.5B-Instruct model to analyze user prompt and generate
    a validated structured video production plan (scenes, video prompts, voiceover script).
    Runs in a background thread so the FastAPI event loop remains responsive.
    """
    logger.info(
        f"Generate endpoint called: prompt='{request.prompt[:50]}...', "
        f"duration={request.duration}s, aspect_ratio={request.aspect_ratio}, "
        f"language={request.language}"
    )

    try:
        # Run blocking model inference in thread pool to avoid blocking the event loop
        plan = await asyncio.to_thread(llm_service.generate_plan, request)
        device_info = llm_service.get_device_info()

        return GenerateResponse(
            status="success",
            message="Structured video plan generated successfully using local Qwen2.5-1.5B-Instruct.",
            request=request,
            plan=plan,
            device_info=device_info
        )
    except Exception as exc:
        logger.error(f"Error during video plan generation: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate video plan: {str(exc)}"
        )


@router.post(
    "/unload-model",
    summary="Unload Qwen LLM from memory to free VRAM"
)
async def unload_model():
    """Explicitly frees Qwen model memory (useful before loading next sequential pipeline models)."""
    await asyncio.to_thread(llm_service.unload_model)
    return {
        "status": "success",
        "message": "Qwen LLM model unloaded successfully.",
        "device_info": llm_service.get_device_info()
    }
