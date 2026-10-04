import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Server & Environment
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

    # LLM Settings (openai, anthropic, gemini, ollama, mock)
    LLM_PROVIDER: str = "mock"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str = ""
    LLM_TEMPERATURE: float = 0.0

    # Embedding Settings
    EMBEDDING_PROVIDER: str = "sentence-transformers"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Storage Paths (resolved relative to workspace/backend root)
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    CHROMA_PATH: str = os.path.join(BASE_DIR, "..", "data", "chroma")
    DATABASE_URL: str = f"sqlite:///{os.path.join(BASE_DIR, '..', 'data', 'autosar_hld.db')}"
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "..", "data", "uploads")
    PROCESSED_DIR: str = os.path.join(BASE_DIR, "..", "data", "processed")
    SAMPLE_DIR: str = os.path.join(BASE_DIR, "..", "data", "sample")

    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = ["pdf"]

    # Chunking & Vector Store Configuration (Phase 3)
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 80
    CHROMA_COLLECTION_NAME: str = "autosar_hld_chunks"
    EMBEDDING_BATCH_SIZE: int = 32

    model_config = {
        "env_file": os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

# Ensure directory paths exist
settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.PROCESSED_DIR, exist_ok=True)
os.makedirs(settings.CHROMA_PATH, exist_ok=True)
os.makedirs(settings.SAMPLE_DIR, exist_ok=True)
