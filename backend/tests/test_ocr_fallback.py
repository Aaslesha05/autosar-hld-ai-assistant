"""
test_ocr_fallback.py
--------------------
Dedicated Phase 2 OCR fallback verification test.

Tests that:
1. A genuine image-only PDF (no embedded text layer) is correctly detected as needing OCR.
2. The OCR fallback is invoked (or gracefully skipped if Tesseract is absent).
3. When Tesseract IS available: is_ocr=True, non-empty text, page number preserved, DB persisted.
4. When Tesseract is NOT available: graceful fallback message stored, no crash.
"""

import os
import io
import json
import pytest
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.ingestion.pdf_processor import PDFProcessor
from app.core.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_image_only_pdf_bytes() -> bytes:
    """
    Create a single-page PDF where the page content is a PNG image containing
    AUTOSAR text rendered by PIL. There is NO embedded text layer whatsoever.
    PyMuPDF get_text() returns an empty string on this page.
    """
    # --- Render text as image at 150 DPI (A4: 1240 x 1754 px) ---
    width, height = 1240, 1754
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Try system fonts, fall back to PIL default
    font_h = font_b = None
    for fname in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "cour.ttf", "FreeMono.ttf"]:
        for fdir in [
            "C:/Windows/Fonts",
            "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/truetype/freefont",
            "/usr/share/fonts/truetype/liberation",
        ]:
            fp = os.path.join(fdir, fname)
            if os.path.exists(fp):
                try:
                    font_h = ImageFont.truetype(fp, 56)
                    font_b = ImageFont.truetype(fp, 38)
                    break
                except Exception:
                    pass
        if font_h:
            break
    if not font_h:
        font_h = font_b = ImageFont.load_default()

    lines = [
        (font_h, "AUTOSAR HLD — Scanned Reference Page"),
        (font_b, ""),
        (font_b, "Section 7: Memory Map Configuration (Scanned)"),
        (font_b, ""),
        (font_b, "BodyControlSWC    ASIL-B  0x20000000"),
        (font_b, "DoorControlSWC    ASIL-B  0x20008000"),
        (font_b, "LightingSWC       ASIL-A  0x20010000"),
        (font_b, ""),
        (font_b, "E2E Profile 01 enforced on ASIL-B inter-SWC signals."),
        (font_b, "ISO 26262 ASIL-B: memory partition via MPU enabled."),
        (font_b, ""),
        (font_h, "Section 8: Runnable Timing"),
        (font_b, ""),
        (font_b, "Run_ReadDoorSensors   20 ms cyclic  priority 5"),
        (font_b, "Run_ProcessDoorEvents 10 ms cyclic  priority 8"),
        (font_b, "Run_LightControl      50 ms cyclic  priority 3"),
        (font_b, ""),
        (font_b, "--- IMAGE-ONLY PAGE: no embedded text layer ---"),
    ]

    y = 80
    for font, text in lines:
        draw.text((80, y), text, fill=(0, 0, 0), font=font)
        y += 64

    # --- Encode image as PNG bytes ---
    png_buf = io.BytesIO()
    img.save(png_buf, format="PNG")
    png_buf.seek(0)

    # --- Embed image into PDF — no text inserted ---
    pdf_doc = fitz.open()
    page = pdf_doc.new_page(width=595, height=842)  # A4 in points
    page.insert_image(fitz.Rect(0, 0, 595, 842), stream=png_buf.read())
    pdf_bytes = pdf_doc.tobytes()
    pdf_doc.close()
    return pdf_bytes


def _check_tesseract_available() -> bool:
    """Check whether the Tesseract binary is callable."""
    return PDFProcessor.is_ocr_available()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def image_only_pdf_bytes() -> bytes:
    """Single-page image-only PDF with AUTOSAR text rendered as an image."""
    return _build_image_only_pdf_bytes()


@pytest.fixture(scope="module")
def tesseract_available() -> bool:
    return _check_tesseract_available()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_image_pdf_has_no_native_text(image_only_pdf_bytes):
    """
    Prerequisite: confirm the test PDF has zero (or near-zero) native text.
    This validates that the PDF fixture is genuinely image-only.
    """
    doc = fitz.open(stream=image_only_pdf_bytes, filetype="pdf")
    native_text = doc[0].get_text("text").strip()
    doc.close()
    assert len(native_text) < 40, (
        f"Expected image-only PDF to have <40 chars of native text, "
        f"but got {len(native_text)} chars: {native_text[:80]!r}"
    )


@pytest.mark.asyncio
async def test_ocr_fallback_invoked_when_tesseract_available(image_only_pdf_bytes, tesseract_available):
    """
    When Tesseract IS available:
    - OCR fallback must be invoked for the image-only page.
    - is_ocr must be True.
    - Extracted text must be non-empty and contain recognizable AUTOSAR content.
    - Page number must be preserved as 1.
    - Persisted DB result must reflect is_ocr=True.
    - Structured JSON file must record ocr_pages_count >= 1.
    """
    if not tesseract_available:
        pytest.skip("Tesseract not installed — skipping live OCR assertion test.")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload the image-only PDF
        files = {"file": ("Scanned_AUTOSAR_HLD.pdf", image_only_pdf_bytes, "application/pdf")}
        up_res = await client.post(
            "/api/documents/upload",
            files=files,
            data={"title": "Scanned AUTOSAR OCR Test", "version_tag": "ocr-test"}
        )
        assert up_res.status_code == 201, f"Upload failed: {up_res.text}"
        doc_id = up_res.json()["document"]["id"]

        # 2. Trigger processing pipeline
        proc_res = await client.post(f"/api/documents/{doc_id}/process")
        assert proc_res.status_code == 200, f"Processing failed: {proc_res.text}"
        data = proc_res.json()

        assert data["status"] == "processed"
        assert data["total_pages_processed"] == 1
        assert data["ocr_pages_count"] >= 1, (
            f"Expected at least 1 OCR page but got {data['ocr_pages_count']}. "
            f"Page cleaned_text: {data['pages'][0].get('cleaned_text', '')[:200]!r}"
        )

        page = data["pages"][0]

        # 3. Page number preservation
        assert page["page_number"] == 1

        # 4. is_ocr must be True
        assert page["is_ocr"] is True, (
            f"Expected is_ocr=True for image-only page, but got is_ocr={page['is_ocr']}. "
            f"Extracted text: {page['cleaned_text'][:200]!r}"
        )

        # 5. Extracted OCR text must be non-empty and contain readable AUTOSAR content
        ocr_text = page["cleaned_text"]
        assert len(ocr_text) > 20, (
            f"Expected non-trivial OCR text, got only {len(ocr_text)} chars: {ocr_text!r}"
        )
        # OCR should pick up at least some recognizable keywords
        ocr_upper = ocr_text.upper()
        found_keywords = [kw for kw in ["AUTOSAR", "ASIL", "SWC", "MEMORY", "SECTION", "PROFILE", "RUNNABLE"]
                          if kw in ocr_upper]
        assert len(found_keywords) >= 1, (
            f"Expected OCR text to contain AUTOSAR-domain keywords. "
            f"Got: {ocr_text[:300]!r}"
        )

        # 6. status must be 'success' (not 'empty_or_scanned')
        assert page["status"] == "success"

        # 7. Retrieve from DB via API — verify persistence
        pages_res = await client.get(f"/api/documents/{doc_id}/pages")
        assert pages_res.status_code == 200
        db_pages = pages_res.json()
        assert len(db_pages) == 1

        db_page = db_pages[0]
        assert db_page["page_number"] == 1
        assert db_page["is_ocr"] is True
        assert len(db_page["cleaned_text"]) > 20

        # 8. Retrieve specific page by number
        pg1_res = await client.get(f"/api/documents/{doc_id}/pages/1")
        assert pg1_res.status_code == 200
        pg1 = pg1_res.json()
        assert pg1["is_ocr"] is True
        assert pg1["page_number"] == 1

        # 9. Verify structured JSON file on disk
        json_path = os.path.join(settings.PROCESSED_DIR, f"{doc_id}.json")
        assert os.path.exists(json_path), f"Processed JSON missing at: {json_path}"
        with open(json_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        assert saved["document_id"] == doc_id
        assert saved["ocr_pages_count"] >= 1
        assert saved["pages"][0]["is_ocr"] is True


@pytest.mark.asyncio
async def test_hybrid_document_page_number_and_ocr_traceability(tesseract_available):
    """
    Demonstrates:
    - Multi-page document where Page 1 is vector text and Page 2 is a scanned image.
    - Page 1 has is_ocr=False, preserves page_number=1.
    - Page 2 has is_ocr=True, preserves page_number=2.
    - Traceability from source document -> page number -> extracted OCR content.
    - Both pages persisted to SQLite document_pages and JSON output.
    """
    if not tesseract_available:
        pytest.skip("Tesseract not installed — skipping live OCR assertion test.")

    # 1. Build 2-page hybrid PDF
    pdf_doc = fitz.open()
    # Page 1: Vector text
    p1 = pdf_doc.new_page(width=595, height=842)
    p1.insert_text((50, 50), "AUTOSAR High Level Design Specification Page 1")
    p1.insert_text((50, 80), "BodyControlSWC architecture overview and normal vector content.")

    # Page 2: Image-only scanned content (rendered PNG bytes from helper)
    img_bytes = _build_image_only_pdf_bytes()
    img_doc = fitz.open(stream=img_bytes, filetype="pdf")
    img_pix = img_doc[0].get_pixmap(dpi=150)
    p2 = pdf_doc.new_page(width=595, height=842)
    p2.insert_image(fitz.Rect(0, 0, 595, 842), pixmap=img_pix)
    img_doc.close()

    hybrid_bytes = pdf_doc.tobytes()
    pdf_doc.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("Hybrid_AUTOSAR_Doc.pdf", hybrid_bytes, "application/pdf")}
        up_res = await client.post(
            "/api/documents/upload",
            files=files,
            data={"title": "Hybrid Vector + Scanned HLD", "version_tag": "hybrid-v1"}
        )
        assert up_res.status_code == 201
        doc_id = up_res.json()["document"]["id"]

        proc_res = await client.post(f"/api/documents/{doc_id}/process")
        assert proc_res.status_code == 200
        proc_data = proc_res.json()

        assert proc_data["total_pages_processed"] == 2
        assert proc_data["ocr_pages_count"] == 1

        pages = proc_data["pages"]
        # Page 1 check
        assert pages[0]["page_number"] == 1
        assert pages[0]["is_ocr"] is False
        assert "BodyControlSWC architecture overview" in pages[0]["cleaned_text"]

        # Page 2 check
        assert pages[1]["page_number"] == 2
        assert pages[1]["is_ocr"] is True
        assert len(pages[1]["cleaned_text"]) > 20
        assert "AUTOSAR" in pages[1]["cleaned_text"].upper()

        # Database verification via GET /api/documents/{doc_id}/pages
        pages_res = await client.get(f"/api/documents/{doc_id}/pages")
        assert pages_res.status_code == 200
        db_pages = pages_res.json()
        assert len(db_pages) == 2
        assert db_pages[0]["page_number"] == 1
        assert db_pages[0]["is_ocr"] is False
        assert db_pages[1]["page_number"] == 2
        assert db_pages[1]["is_ocr"] is True

        # Database verification via single page endpoint
        p2_res = await client.get(f"/api/documents/{doc_id}/pages/2")
        assert p2_res.status_code == 200
        assert p2_res.json()["page_number"] == 2
        assert p2_res.json()["is_ocr"] is True


@pytest.mark.asyncio
async def test_ocr_graceful_degradation_without_tesseract(image_only_pdf_bytes, tesseract_available):
    """
    When Tesseract is NOT installed:
    - Pipeline must not crash.
    - Fallback message is stored in cleaned_text.
    - is_ocr must be False (OCR was not successfully executed).
    - Page status is 'empty_or_scanned'.
    - Document status is still 'processed'.
    """
    if tesseract_available:
        pytest.skip("Tesseract IS installed — degradation test not applicable.")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("Scanned_NTesseract.pdf", image_only_pdf_bytes, "application/pdf")}
        up_res = await client.post("/api/documents/upload", files=files)
        assert up_res.status_code == 201
        doc_id = up_res.json()["document"]["id"]

        proc_res = await client.post(f"/api/documents/{doc_id}/process")
        assert proc_res.status_code == 200, f"Processing crashed: {proc_res.text}"
        data = proc_res.json()

        # Document-level: must still complete
        assert data["status"] == "processed"
        assert data["total_pages_processed"] == 1
        assert data["ocr_pages_count"] == 0  # no successful OCR

        page = data["pages"][0]
        assert page["page_number"] == 1
        assert page["is_ocr"] is False

        # Fallback message must be present
        assert "Tesseract" in page["cleaned_text"] or "scanned" in page["cleaned_text"].lower() or \
               "empty_or_scanned" == page["status"], (
            f"Expected graceful OCR fallback message, got: {page['cleaned_text']!r}"
        )

        # Page status must reflect it was scanned/unreadable
        assert page["status"] == "empty_or_scanned", (
            f"Expected status='empty_or_scanned', got: {page['status']!r}"
        )
