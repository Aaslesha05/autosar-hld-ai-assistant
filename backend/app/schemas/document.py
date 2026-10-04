from pydantic import BaseModel, Field
from typing import Optional, List

class DocumentBase(BaseModel):
    title: Optional[str] = None
    version_tag: Optional[str] = "v1.0"

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(BaseModel):
    id: str
    filename: str
    stored_filename: str
    file_size_bytes: int
    file_hash: str
    page_count: int
    status: str
    error_message: Optional[str] = None
    title: Optional[str] = None
    version_tag: Optional[str] = "v1.0"
    created_at: str
    updated_at: str

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int

class DocumentUploadResponse(BaseModel):
    message: str
    document: DocumentResponse
