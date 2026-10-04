from pydantic import BaseModel
from typing import Dict, Any

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    llm_provider: str
    embedding_provider: str
    details: Dict[str, Any]
