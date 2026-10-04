import os
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    System health check endpoint verifying core backend configuration and storage paths.
    """
    chroma_ok = os.path.exists(settings.CHROMA_PATH)
    upload_ok = os.path.exists(settings.UPLOAD_DIR)
    processed_ok = os.path.exists(settings.PROCESSED_DIR)

    return HealthResponse(
        status="healthy",
        service="AUTOSAR HLD AI Assistant",
        version="0.1.0",
        environment=settings.ENVIRONMENT,
        llm_provider=settings.LLM_PROVIDER,
        embedding_provider=settings.EMBEDDING_PROVIDER,
        details={
            "storage": {
                "chroma_dir_exists": chroma_ok,
                "upload_dir_exists": upload_ok,
                "processed_dir_exists": processed_ok
            },
            "config": {
                "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
                "allowed_extensions": settings.ALLOWED_EXTENSIONS
            }
        }
    )
