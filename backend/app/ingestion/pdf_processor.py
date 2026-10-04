import os
import io
import re
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

import pymupdf as fitz
from PIL import Image
try:
    import pytesseract
except ImportError:
    pytesseract = None

from fastapi import HTTPException, status

# ---------------------------------------------------------------------------
# Windows Tesseract path discovery
# UB-Mannheim installer default location — probed at module load time.
# ---------------------------------------------------------------------------
_WINDOWS_TESSERACT_CANDIDATES = [
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    r"C:\Users\aasle\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

def _probe_and_set_tesseract_path() -> None:
    """If running on Windows and Tesseract is not on PATH, attempt to locate
    the binary at standard install locations and configure pytesseract to use it."""
    if pytesseract is None:
        return
    import shutil
    for candidate in _WINDOWS_TESSERACT_CANDIDATES:
        if os.path.isfile(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            tessdata_dir = os.path.join(os.path.dirname(candidate), "tessdata")
            if os.path.isdir(tessdata_dir) and "TESSDATA_PREFIX" not in os.environ:
                os.environ["TESSDATA_PREFIX"] = tessdata_dir
            return
    if shutil.which("tesseract"):
        return  # already on PATH — nothing to do

_probe_and_set_tesseract_path()
from app.core.config import settings
from app.core.database import get_connection
from app.schemas.page import DocumentPageResponse, DocumentProcessingResponse, TableData

logger = logging.getLogger("autosar_hld_pdf_processor")

class PDFProcessor:
    @staticmethod
    def is_ocr_available() -> bool:
        """Check if pytesseract and tesseract executable are available."""
        if pytesseract is None:
            return False
        # Re-probe path each call in case binary appeared after module import
        _probe_and_set_tesseract_path()
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize extracted text while preserving structural paragraphs."""
        if not text:
            return ""
        # Replace multiple horizontal spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)
        # Normalize carriage returns
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # Limit consecutive newlines to 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @classmethod
    def extract_headings(cls, page: fitz.Page, page_text: str) -> List[str]:
        """
        Detect architectural headings using font size and text formatting heuristics.
        """
        headings: List[str] = []
        try:
            blocks = page.get_text("dict").get("blocks", [])
            span_sizes = []
            
            # First pass: collect font sizes
            for b in blocks:
                if "lines" in b:
                    for line in b["lines"]:
                        for span in line.get("spans", []):
                            txt = span.get("text", "").strip()
                            if txt and len(txt) > 2:
                                span_sizes.append(span.get("size", 10.0))

            median_size = 10.0
            if span_sizes:
                sorted_sizes = sorted(span_sizes)
                median_size = sorted_sizes[len(sorted_sizes) // 2]

            # Second pass: identify headings
            for b in blocks:
                if "lines" in b:
                    for line in b["lines"]:
                        line_text = " ".join([s.get("text", "").strip() for s in line.get("spans", [])]).strip()
                        if not line_text or len(line_text) < 3:
                            continue
                        
                        max_span_size = max([s.get("size", 10.0) for s in line.get("spans", [])], default=10.0)
                        is_bold = any((s.get("flags", 0) & 2 != 0) or ("bold" in s.get("font", "").lower()) for s in line.get("spans", []))

                        # Heading heuristics:
                        # 1. Significantly larger font
                        # 2. Numbered section (e.g., '1. System Architectural Overview', 'Section 2.3')
                        # 3. Bold title-like short line
                        is_numbered_section = bool(re.match(r'^\s*(\d+\.|\d+\.\d+|Section\s+\d+|Scenario\s+\d+)', line_text, re.IGNORECASE))
                        
                        if (max_span_size >= median_size * 1.25) or (is_bold and len(line_text) < 100) or (is_numbered_section and len(line_text) < 120):
                            if line_text not in headings:
                                headings.append(line_text)
        except Exception as e:
            logger.warning(f"Heading extraction failed for page: {e}")
            # Fallback to regex on raw text
            for line in page_text.split('\n'):
                line_str = line.strip()
                if re.match(r'^\s*(\d+\.|\d+\.\d+|Section\s+\d+|Scenario\s+\d+)', line_str, re.IGNORECASE) and len(line_str) < 120:
                    if line_str not in headings:
                        headings.append(line_str)

        return headings

    @classmethod
    def extract_tables(cls, page: fitz.Page) -> List[TableData]:
        """
        Extract tabular data using PyMuPDF's built-in table recognition engine.
        """
        tables_found: List[TableData] = []
        try:
            tabs = page.find_tables()
            for idx, tab in enumerate(tabs.tables):
                extracted_rows = tab.extract()
                if extracted_rows and len(extracted_rows) > 0:
                    cleaned_rows = []
                    for row in extracted_rows:
                        cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                        cleaned_rows.append(cleaned_row)
                    
                    row_count = len(cleaned_rows)
                    col_count = len(cleaned_rows[0]) if row_count > 0 else 0

                    tables_found.append(TableData(
                        table_index=idx,
                        rows=cleaned_rows,
                        row_count=row_count,
                        col_count=col_count
                    ))
        except Exception as e:
            logger.warning(f"Table extraction error: {e}")

        return tables_found

    @classmethod
    def perform_ocr(cls, page: fitz.Page) -> Tuple[str, bool]:
        """
        Attempt OCR on a page when native text is missing or sparse.
        Returns (extracted_text, ocr_succeeded).
        """
        if not cls.is_ocr_available():
            logger.info("OCR requested but Tesseract is not available on host system.")
            return "[Scanned page detected: Tesseract OCR engine not installed on host PATH; native text empty.]", False

        try:
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes()))
            ocr_text = pytesseract.image_to_string(img)
            return cls.clean_text(ocr_text), True
        except Exception as e:
            logger.error(f"OCR execution failed: {e}")
            return f"[OCR execution error: {str(e)}]", False

    @classmethod
    def process_document(cls, document_id: str) -> DocumentProcessingResponse:
        """
        Executes the full PDF processing pipeline:
        1. Fetch document from DB.
        2. Set status to 'processing'.
        3. Parse each page (text, headings, tables, scanned detection/OCR).
        4. Persist pages to SQLite document_pages table.
        5. Persist JSON output file in data/processed/.
        6. Set document status to 'processed'.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?;", (document_id,))
        doc_row = cursor.fetchone()

        if not doc_row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{document_id}' not found."
            )

        file_path = doc_row["file_path"]
        if not os.path.exists(file_path):
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document file does not exist on disk at path: {file_path}"
            )

        # Update status to 'processing'
        now_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "UPDATE documents SET status = 'processing', updated_at = ? WHERE id = ?;",
            (now_iso, document_id)
        )
        conn.commit()

        processed_pages: List[DocumentPageResponse] = []
        total_words = 0
        ocr_pages_count = 0
        tables_found_count = 0

        try:
            pdf_doc = fitz.open(file_path)
            total_pages = len(pdf_doc)

            # Clear any previously processed pages for idempotent reprocessing
            cursor.execute("DELETE FROM document_pages WHERE document_id = ?;", (document_id,))
            conn.commit()

            for page_idx, page in enumerate(pdf_doc, start=1):
                raw_text = page.get_text("text")
                cleaned_text = cls.clean_text(raw_text)
                is_ocr = False
                page_status = "success"

                # Check if page is image-based or has minimal text (< 40 characters)
                if len(cleaned_text) < 40:
                    # Check for images or low text
                    ocr_text, ocr_success = cls.perform_ocr(page)
                    if ocr_success and len(ocr_text) > len(cleaned_text):
                        cleaned_text = ocr_text
                        raw_text = ocr_text
                        is_ocr = True
                        ocr_pages_count += 1
                    elif not ocr_success and len(cleaned_text) == 0:
                        page_status = "empty_or_scanned"

                # Extract headings
                headings = cls.extract_headings(page, cleaned_text)

                # Extract tables
                tables = cls.extract_tables(page)
                has_tables = len(tables) > 0
                if has_tables:
                    tables_found_count += len(tables)

                word_count = len(cleaned_text.split())
                char_count = len(cleaned_text)
                total_words += word_count

                page_id = str(uuid.uuid4())
                page_now = datetime.now(timezone.utc).isoformat()

                headings_json = json.dumps(headings)
                tables_json = json.dumps([t.model_dump() for t in tables])

                # Save to database
                cursor.execute("""
                    INSERT INTO document_pages (
                        id, document_id, page_number, raw_text, cleaned_text,
                        headings_json, tables_json, has_tables, is_ocr,
                        word_count, char_count, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    page_id,
                    document_id,
                    page_idx,
                    raw_text,
                    cleaned_text,
                    headings_json,
                    tables_json,
                    1 if has_tables else 0,
                    1 if is_ocr else 0,
                    word_count,
                    char_count,
                    page_status,
                    page_now
                ))

                processed_pages.append(DocumentPageResponse(
                    id=page_id,
                    document_id=document_id,
                    page_number=page_idx,
                    raw_text=raw_text,
                    cleaned_text=cleaned_text,
                    headings=headings,
                    tables=tables,
                    has_tables=has_tables,
                    is_ocr=is_ocr,
                    word_count=word_count,
                    char_count=char_count,
                    status=page_status,
                    created_at=page_now
                ))

            pdf_doc.close()

            # Save structured output file in data/processed/
            processed_file_path = os.path.join(settings.PROCESSED_DIR, f"{document_id}.json")
            structured_data = {
                "document_id": document_id,
                "filename": doc_row["filename"],
                "version_tag": doc_row["version_tag"],
                "total_pages": total_pages,
                "total_words": total_words,
                "tables_count": tables_found_count,
                "ocr_pages_count": ocr_pages_count,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "pages": [p.model_dump() for p in processed_pages]
            }
            with open(processed_file_path, "w", encoding="utf-8") as f:
                json.dump(structured_data, f, indent=2)

            # Update document record to 'processed'
            finish_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                UPDATE documents 
                SET status = 'processed', page_count = ?, error_message = NULL, updated_at = ?
                WHERE id = ?;
            """, (total_pages, finish_iso, document_id))
            conn.commit()

            return DocumentProcessingResponse(
                message=f"Document successfully processed. {total_pages} pages extracted.",
                document_id=document_id,
                status="processed",
                total_pages_processed=total_pages,
                ocr_pages_count=ocr_pages_count,
                tables_found_count=tables_found_count,
                total_words=total_words,
                pages=processed_pages
            )

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}", exc_info=True)
            fail_iso = datetime.now(timezone.utc).isoformat()
            error_msg = f"Document processing failed: {str(e)}"
            cursor.execute("""
                UPDATE documents 
                SET status = 'failed', error_message = ?, updated_at = ?
                WHERE id = ?;
            """, (error_msg, fail_iso, document_id))
            conn.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Document processing failed: {str(e)}"
            )
        finally:
            conn.close()

    @staticmethod
    def get_document_pages(document_id: str) -> List[DocumentPageResponse]:
        """Fetch all processed pages for a document ordered by page_number ASC."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM document_pages 
            WHERE document_id = ? 
            ORDER BY page_number ASC;
        """, (document_id,))
        rows = cursor.fetchall()
        conn.close()

        pages = []
        for r in rows:
            headings = json.loads(r["headings_json"]) if r["headings_json"] else []
            tables_data = json.loads(r["tables_json"]) if r["tables_json"] else []
            tables = [TableData(**t) for t in tables_data]

            pages.append(DocumentPageResponse(
                id=r["id"],
                document_id=r["document_id"],
                page_number=r["page_number"],
                raw_text=r["raw_text"],
                cleaned_text=r["cleaned_text"],
                headings=headings,
                tables=tables,
                has_tables=bool(r["has_tables"]),
                is_ocr=bool(r["is_ocr"]),
                word_count=r["word_count"],
                char_count=r["char_count"],
                status=r["status"],
                created_at=r["created_at"]
            ))
        return pages

    @staticmethod
    def get_document_page(document_id: str, page_number: int) -> Optional[DocumentPageResponse]:
        """Fetch a specific processed page by page_number."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM document_pages 
            WHERE document_id = ? AND page_number = ?;
        """, (document_id, page_number))
        r = cursor.fetchone()
        conn.close()

        if not r:
            return None

        headings = json.loads(r["headings_json"]) if r["headings_json"] else []
        tables_data = json.loads(r["tables_json"]) if r["tables_json"] else []
        tables = [TableData(**t) for t in tables_data]

        return DocumentPageResponse(
            id=r["id"],
            document_id=r["document_id"],
            page_number=r["page_number"],
            raw_text=r["raw_text"],
            cleaned_text=r["cleaned_text"],
            headings=headings,
            tables=tables,
            has_tables=bool(r["has_tables"]),
            is_ocr=bool(r["is_ocr"]),
            word_count=r["word_count"],
            char_count=r["char_count"],
            status=r["status"],
            created_at=r["created_at"]
        )
