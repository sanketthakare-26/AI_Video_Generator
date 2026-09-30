from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config.settings import settings
from app.utils.logger import logger

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Local AI Video Generator Backend Foundation",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],  # Allow configured local origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Clean validation error response without leaking internal structures."""
    error_details = []
    for err in exc.errors():
        field = " -> ".join([str(loc) for loc in err.get("loc", []) if loc != "body"])
        msg = err.get("msg", "Invalid value")
        error_details.append(f"{field}: {msg}" if field else msg)

    logger.warning(f"Validation error on {request.url.path}: {error_details}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": "Validation failed. " + "; ".join(error_details),
            "errors": error_details
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected server errors cleanly."""
    logger.error(f"Unhandled error processing {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "An internal server error occurred. Please try again later."
        }
    )


# Mount API routes
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", summary="Root Index")
async def root():
    return {
        "message": "Welcome to AI Video Generator API. Access endpoints under /api or view /docs."
    }
