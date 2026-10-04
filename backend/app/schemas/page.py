from pydantic import BaseModel, Field
from typing import List, Optional, Any

class TableData(BaseModel):
    table_index: int
    rows: List[List[Optional[str]]]
    row_count: int
    col_count: int

class DocumentPageResponse(BaseModel):
    id: str
    document_id: str
    page_number: int
    raw_text: str
    cleaned_text: str
    headings: List[str] = Field(default_factory=list)
    tables: List[TableData] = Field(default_factory=list)
    has_tables: bool
    is_ocr: bool
    word_count: int
    char_count: int
    status: str
    created_at: str

class DocumentProcessingResponse(BaseModel):
    message: str
    document_id: str
    status: str
    total_pages_processed: int
    ocr_pages_count: int
    tables_found_count: int
    total_words: int
    pages: List[DocumentPageResponse]
