import os
import re
import uuid
import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import pymupdf as fitz
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.core.database import get_connection
from app.schemas.document import DocumentResponse

class DocumentService:
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Strip directory paths and sanitize file name to prevent directory traversal."""
        base = os.path.basename(filename)
        clean = re.sub(r'[^\w\.-]', '_', base)
        return clean or "document.pdf"

    @staticmethod
    def calculate_sha256(content: bytes) -> str:
        """Compute SHA-256 hash of file content."""
        hasher = hashlib.sha256()
        hasher.update(content)
        return hasher.hexdigest()

    @staticmethod
    def validate_pdf(content: bytes, original_filename: str) -> Tuple[int, Optional[str]]:
        """
        Validate PDF magic bytes, extension, and integrity using PyMuPDF.
        Returns (page_count, error_message).
        """
        # 1. Extension check
        if not original_filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension. Only PDF files are supported (got '{original_filename}')."
            )

        # 2. Magic bytes check
        if not content.startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. File does not start with standard PDF header (%PDF)."
            )

        # 3. Minimum size check (an empty/truncated file)
        if len(content) < 32:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty or corrupted (size < 32 bytes)."
            )

        # 4. PyMuPDF integrity & page count check
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            page_count = len(doc)
            doc.close()
            if page_count == 0:
                return 0, "PDF contains no renderable pages."
            return page_count, None
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to parse PDF document structure: {str(e)}"
            )

    @classmethod
    async def upload_document(
        cls, 
        file: UploadFile, 
        title: Optional[str] = None, 
        version_tag: Optional[str] = "v1.0"
    ) -> DocumentResponse:
        """Handle upload, validation, disk storage, and database registration."""
        filename = file.filename or "unnamed.pdf"
        sanitized_filename = cls.sanitize_filename(filename)

        # Read content
        content = await file.read()
        file_size_bytes = len(content)

        # File size check
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size_bytes > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE if hasattr(status, "HTTP_413_CONTENT_TOO_LARGE") else 413,
                detail=f"File size ({file_size_bytes / (1024 * 1024):.2f} MB) exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB} MB."
            )

        # Validate PDF content & get page count
        page_count, validation_error = cls.validate_pdf(content, sanitized_filename)

        # Hash calculation
        file_hash = cls.calculate_sha256(content)

        # Generate unique document ID and safe storage path
        doc_id = str(uuid.uuid4())
        stored_filename = f"{doc_id}_{sanitized_filename}"
        file_path = os.path.join(settings.UPLOAD_DIR, stored_filename)

        # Write to disk securely
        try:
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to write uploaded file to storage: {str(e)}"
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        initial_status = "uploaded" if not validation_error else "failed"

        # Record in database
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO documents (
                id, filename, stored_filename, file_path, file_size_bytes,
                file_hash, page_count, status, error_message, title,
                version_tag, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            sanitized_filename,
            stored_filename,
            file_path,
            file_size_bytes,
            file_hash,
            page_count,
            initial_status,
            validation_error,
            title or sanitized_filename,
            version_tag or "v1.0",
            now_iso,
            now_iso
        ))
        conn.commit()
        conn.close()

        return DocumentResponse(
            id=doc_id,
            filename=sanitized_filename,
            stored_filename=stored_filename,
            file_size_bytes=file_size_bytes,
            file_hash=file_hash,
            page_count=page_count,
            status=initial_status,
            error_message=validation_error,
            title=title or sanitized_filename,
            version_tag=version_tag or "v1.0",
            created_at=now_iso,
            updated_at=now_iso
        )

    @staticmethod
    def list_documents() -> List[DocumentResponse]:
        """Fetch all documents sorted by upload time descending."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents ORDER BY created_at DESC;")
        rows = cursor.fetchall()
        conn.close()

        results = []
        for r in rows:
            results.append(DocumentResponse(
                id=r["id"],
                filename=r["filename"],
                stored_filename=r["stored_filename"],
                file_size_bytes=r["file_size_bytes"],
                file_hash=r["file_hash"],
                page_count=r["page_count"],
                status=r["status"],
                error_message=r["error_message"],
                title=r["title"],
                version_tag=r["version_tag"],
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            ))
        return results

    @staticmethod
    def get_document(doc_id: str) -> Optional[DocumentResponse]:
        """Fetch a single document by ID."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?;", (doc_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return DocumentResponse(
            id=row["id"],
            filename=row["filename"],
            stored_filename=row["stored_filename"],
            file_size_bytes=row["file_size_bytes"],
            file_hash=row["file_hash"],
            page_count=row["page_count"],
            status=row["status"],
            error_message=row["error_message"],
            title=row["title"],
            version_tag=row["version_tag"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    @staticmethod
    def delete_document(doc_id: str) -> bool:
        """Delete document record and associated file on disk."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM documents WHERE id = ?;", (doc_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False

        file_path = row["file_path"]
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

        # Delete processed JSON artifact if exists
        processed_json = os.path.join(settings.PROCESSED_DIR, f"{doc_id}.json")
        if os.path.exists(processed_json):
            try:
                os.remove(processed_json)
            except OSError:
                pass

        # Delete vectors from ChromaDB if any exist
        try:
            from app.ingestion.vector_store import get_vector_store
            get_vector_store().delete_document_vectors(doc_id)
        except Exception:
            pass

        cursor.execute("DELETE FROM documents WHERE id = ?;", (doc_id,))
        conn.commit()
        conn.close()
        return True
