"""
rag.py
------
Pydantic schemas for Phase 4 RAG question-answering, citation traceability,
and retrieval metadata.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class Citation(BaseModel):
    citation_index: int = Field(..., description="1-based index of citation in response")
    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Source document UUID")
    filename: str = Field(..., description="Original PDF filename")
    version_tag: str = Field(..., description="Document architectural version")
    page_number: int = Field(..., description="1-indexed source PDF page")
    heading: str = Field(..., description="Architectural section title")
    source_type: str = Field(..., description="'text', 'table', or 'ocr'")
    similarity_score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    snippet: str = Field(..., description="Excerpt of the retrieved evidence")


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    version_tag: str
    page_number: int
    heading: str
    source_type: str
    is_ocr: bool
    distance: float
    similarity_score: float
    content: str


class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, description="User architectural inquiry")
    document_id: Optional[str] = Field(None, description="Optional document UUID filter")
    version_tag: Optional[str] = Field(None, description="Optional HLD revision filter (e.g. 'v1.0', 'v2.0')")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Max chunks to retrieve")
    similarity_threshold: Optional[float] = Field(0.35, ge=0.0, le=1.0, description="Minimum cosine similarity")


class RAGQueryResponse(BaseModel):
    question: str
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    retrieved_chunks: List[RetrievedChunk] = Field(default_factory=list)
    confidence: float = Field(..., description="Retrieval-derived confidence indicator (0.0 to 1.0)")
    confidence_level: str = Field(..., description="'HIGH', 'MEDIUM', 'LOW', or 'INSUFFICIENT'")
    limitations: List[str] = Field(default_factory=list)
    document_id_filter: Optional[str] = None
    version_filter: Optional[str] = None
