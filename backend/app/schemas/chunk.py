from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ChunkMetadata(BaseModel):
    chunk_id: str
    chunk_index: int
    document_id: str
    filename: str
    version_tag: str
    page_number: int
    heading: str = "General"
    source_type: str = "text"  # "text", "table", "ocr"
    is_ocr: bool = False
    word_count: int = 0
    char_count: int = 0

    def to_chroma_metadata(self) -> Dict[str, Any]:
        """Convert metadata to ChromaDB-compatible primitive dictionary."""
        return {
            "chunk_id": str(self.chunk_id),
            "chunk_index": int(self.chunk_index),
            "document_id": str(self.document_id),
            "filename": str(self.filename),
            "version_tag": str(self.version_tag),
            "page_number": int(self.page_number),
            "heading": str(self.heading),
            "source_type": str(self.source_type),
            "is_ocr": bool(self.is_ocr),
            "word_count": int(self.word_count),
            "char_count": int(self.char_count),
        }

class Chunk(BaseModel):
    chunk_id: str
    content: str
    metadata: ChunkMetadata

class DocumentIngestionResponse(BaseModel):
    message: str
    document_id: str
    status: str
    total_chunks: int
    total_vectors: int
    collection_name: str
    embedding_model: str
    ingested_at: str

class DocumentIngestionStatusResponse(BaseModel):
    document_id: str
    status: str
    total_chunks: int
    total_vectors: int
    collection_name: str
    embedding_model: str
    ingested_at: Optional[str] = None
