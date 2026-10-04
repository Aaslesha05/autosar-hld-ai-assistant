import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import api_router
from app.api.health import router as health_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("autosar_hld_backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AUTOSAR HLD AI Assistant Backend...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Chroma DB Path: {settings.CHROMA_PATH}")
    yield
    logger.info("Shutting down AUTOSAR HLD AI Assistant Backend...")

app = FastAPI(
    title="AUTOSAR HLD AI Assistant API",
    version="0.1.0",
    description="Automotive Engineering AI for AUTOSAR High-Level Design documents, RAG retrieval, architectural entity extraction, and consistency validation.",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root-level health check (for simple monitors and proxy pass)
app.include_router(health_router)

# Versioned / modular API router
app.include_router(api_router, prefix="/api")

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to the AUTOSAR HLD AI Assistant API",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
