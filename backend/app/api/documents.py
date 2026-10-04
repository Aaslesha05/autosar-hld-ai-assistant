import os
from typing import Optional, List
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.schemas.document import DocumentListResponse, DocumentResponse, DocumentUploadResponse
from app.schemas.page import DocumentPageResponse, DocumentProcessingResponse
from app.schemas.chunk import DocumentIngestionResponse, DocumentIngestionStatusResponse
from app.services.document_service import DocumentService
from app.ingestion.pdf_processor import PDFProcessor
from app.ingestion.ingestion_service import DocumentIngestionService

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="AUTOSAR HLD PDF Document"),
    title: Optional[str] = Form(None, description="Optional human-readable document title"),
    version_tag: Optional[str] = Form("v1.0", description="Document revision tag (e.g., v1.0, v2.0)")
):
    """
    Upload and validate an AUTOSAR High-Level Design (HLD) PDF document.
    Validates file extension, PDF magic header, size threshold, and structural integrity.
    """
    doc = await DocumentService.upload_document(
        file=file,
        title=title,
        version_tag=version_tag
    )
    return DocumentUploadResponse(
        message=f"Document '{doc.filename}' uploaded successfully.",
        document=doc
    )

@router.get("", response_model=DocumentListResponse)
async def list_documents():
    """
    List all uploaded AUTOSAR HLD documents, sorted by most recent upload.
    """
    docs = DocumentService.list_documents()
    return DocumentListResponse(
        documents=docs,
        total=len(docs)
    )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """
    Get detailed metadata and processing status for an uploaded document.
    """
    doc = DocumentService.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
    return doc

@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(document_id: str):
    """
    Delete an uploaded document, its physical file, and all processed pages.
    """
    deleted = DocumentService.delete_document(document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
    return {"message": f"Document '{document_id}' deleted successfully."}

@router.get("/{document_id}/file")
async def get_document_file(document_id: str):
    """
    Safely download or preview the original uploaded PDF.
    """
    doc = DocumentService.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
    
    from app.core.database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM documents WHERE id = ?;", (document_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not os.path.exists(row["file_path"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical document file missing from storage."
        )

    return FileResponse(
        path=row["file_path"],
        media_type="application/pdf",
        filename=doc.filename
    )

# --- Phase 2: PDF Processing Endpoints ---

@router.post("/{document_id}/process", response_model=DocumentProcessingResponse)
async def process_document(document_id: str):
    """
    Execute the Phase 2 PDF processing pipeline:
    Extract page-by-page text, headings, tables, perform OCR fallback where required,
    and persist structured page metadata.
    """
    return PDFProcessor.process_document(document_id)

@router.get("/{document_id}/pages", response_model=List[DocumentPageResponse])
async def get_document_pages(document_id: str):
    """
    Retrieve all processed pages with extracted text, headings, and tables for an HLD document.
    """
    doc = DocumentService.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
    return PDFProcessor.get_document_pages(document_id)

@router.get("/{document_id}/pages/{page_number}", response_model=DocumentPageResponse)
async def get_document_page(document_id: str, page_number: int):
    """
    Retrieve structured content and metadata for a specific 1-indexed page.
    """
    doc = DocumentService.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
    page = PDFProcessor.get_document_page(document_id, page_number)
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_number} for document '{document_id}' not found or not yet processed."
        )
    return page


# --- Phase 3: Chunking & ChromaDB Ingestion Endpoints ---

@router.post("/{document_id}/ingest", response_model=DocumentIngestionResponse)
async def ingest_document(document_id: str):
    """
    Execute Phase 3 Ingestion Pipeline:
    Generate context-aware chunks, compute SentenceTransformer embeddings,
    and persist vectors with traceable architectural metadata into ChromaDB.
    """
    return DocumentIngestionService.ingest_document(document_id)


@router.get("/{document_id}/ingestion", response_model=DocumentIngestionStatusResponse)
async def get_document_ingestion_status(document_id: str):
    """
    Query the knowledge-base ingestion status, chunk count, and vector count in ChromaDB.
    """
    return DocumentIngestionService.get_ingestion_status(document_id)

