import os
import json
import pytest
from httpx import AsyncClient, ASGITransport
import pymupdf as fitz
from app.main import app
from app.core.config import settings

@pytest.fixture
def v1_pdf_bytes():
    with open("data/sample/AUTOSAR_BodyControl_HLD_v1.0.pdf", "rb") as f:
        return f.read()

@pytest.fixture
def v2_pdf_bytes():
    with open("data/sample/AUTOSAR_BodyControl_HLD_v2.0.pdf", "rb") as f:
        return f.read()

@pytest.fixture
def scanned_or_empty_pdf_bytes():
    """Create a 2-page PDF where page 2 has minimal text (<10 chars) to test OCR / sparse detection."""
    doc = fitz.open()
    # Page 1: normal text
    p1 = doc.new_page()
    p1.insert_text((50, 50), "AUTOSAR Test Header with plenty of text for standard processing.")
    # Page 2: sparse / minimal text (only 5 chars)
    p2 = doc.new_page()
    p2.insert_text((50, 50), "Test")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

@pytest.mark.asyncio
async def test_process_v1_document(v1_pdf_bytes):
    """Test full processing pipeline on AUTOSAR HLD v1.0 PDF with semantic verification."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload document
        files = {"file": ("AUTOSAR_BCM_v1.0.pdf", v1_pdf_bytes, "application/pdf")}
        up_res = await client.post("/api/documents/upload", files=files, data={"version_tag": "v1.0"})
        assert up_res.status_code == 201
        doc_id = up_res.json()["document"]["id"]

        # 2. Trigger processing
        proc_res = await client.post(f"/api/documents/{doc_id}/process")
        assert proc_res.status_code == 200
        data = proc_res.json()
        assert data["status"] == "processed"
        assert data["total_pages_processed"] == 3
        assert len(data["pages"]) == 3

        # 3. Retrieve all pages
        pages_res = await client.get(f"/api/documents/{doc_id}/pages")
        assert pages_res.status_code == 200
        pages = pages_res.json()
        assert len(pages) == 3

        # 4. Strict Page Number Preservation & Semantic Verification
        # Page 1 Verification
        p1 = pages[0]
        assert p1["page_number"] == 1
        assert "System Architectural Overview" in p1["cleaned_text"]
        assert "BodyControlSWC" in p1["cleaned_text"]
        assert "DoorControlSWC" in p1["cleaned_text"]
        assert p1["has_tables"] is True
        assert len(p1["tables"]) >= 1
        p1_table_text = str(p1["tables"][0]["rows"])
        assert "BodyControlSWC" in p1_table_text
        assert "Sensor-Actuator SWC" in p1_table_text

        # Page 2 Verification
        p2 = pages[1]
        assert p2["page_number"] == 2
        assert "Interface and Port Configuration" in p2["cleaned_text"]
        assert "DoorStatus_If" in p2["cleaned_text"]
        assert "LightControl_If" in p2["cleaned_text"]
        assert "PowerMode_If" in p2["cleaned_text"]
        assert p2["has_tables"] is True

        # Page 3 Verification
        p3 = pages[2]
        assert p3["page_number"] == 3
        assert "Scenario 1: Driver Door Unlock Sequence" in p3["cleaned_text"]
        assert "E2E Profile 01" in p3["cleaned_text"]
        assert "ASIL-B" in p3["cleaned_text"]

        # 5. Check persistent structured JSON artifact exists
        json_path = os.path.join(settings.PROCESSED_DIR, f"{doc_id}.json")
        assert os.path.exists(json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            saved_json = json.load(f)
            assert saved_json["document_id"] == doc_id
            assert saved_json["total_pages"] == 3

@pytest.mark.asyncio
async def test_process_v2_document(v2_pdf_bytes):
    """Test full processing pipeline on AUTOSAR HLD v2.0 PDF with semantic verification of changes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("AUTOSAR_BCM_v2.0.pdf", v2_pdf_bytes, "application/pdf")}
        up_res = await client.post("/api/documents/upload", files=files, data={"version_tag": "v2.0"})
        doc_id = up_res.json()["document"]["id"]

        proc_res = await client.post(f"/api/documents/{doc_id}/process")
        assert proc_res.status_code == 200
        pages = proc_res.json()["pages"]

        # Page 1 contains TelematicsGatewaySWC in v2.0
        p1 = pages[0]
        assert "TelematicsGatewaySWC" in p1["cleaned_text"]

        # Page 2 contains RemoteCommand_If in v2.0
        p2 = pages[1]
        assert "RemoteCommand_If" in p2["cleaned_text"]

@pytest.mark.asyncio
async def test_idempotent_reprocessing(v1_pdf_bytes):
    """Verify that reprocessing a document clears old pages and re-populates cleanly without duplicates."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("Reprocess_Test.pdf", v1_pdf_bytes, "application/pdf")}
        up_res = await client.post("/api/documents/upload", files=files)
        doc_id = up_res.json()["document"]["id"]

        # First process
        p1 = await client.post(f"/api/documents/{doc_id}/process")
        assert p1.status_code == 200
        assert p1.json()["total_pages_processed"] == 3

        # Second process (Reprocess)
        p2 = await client.post(f"/api/documents/{doc_id}/process")
        assert p2.status_code == 200
        assert p2.json()["total_pages_processed"] == 3

        # Check total pages in database is strictly 3, NOT 6!
        pages_res = await client.get(f"/api/documents/{doc_id}/pages")
        assert len(pages_res.json()) == 3

@pytest.mark.asyncio
async def test_sparse_or_scanned_page_detection(scanned_or_empty_pdf_bytes):
    """Verify that pages with minimal text trigger scanned detection / OCR fallback checks."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("Sparse_Test.pdf", scanned_or_empty_pdf_bytes, "application/pdf")}
        up_res = await client.post("/api/documents/upload", files=files)
        doc_id = up_res.json()["document"]["id"]

        proc_res = await client.post(f"/api/documents/{doc_id}/process")
        assert proc_res.status_code == 200
        pages = proc_res.json()["pages"]
        assert len(pages) == 2
        # Page 1: normal
        assert pages[0]["page_number"] == 1
        assert "AUTOSAR Test Header" in pages[0]["cleaned_text"]
        # Page 2: sparse / minimal text detected
        assert pages[1]["page_number"] == 2
        assert pages[1]["word_count"] <= 5

@pytest.mark.asyncio
async def test_single_page_retrieval(v1_pdf_bytes):
    """Verify GET /api/documents/{document_id}/pages/{page_number} endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("Page_Retrieval_Test.pdf", v1_pdf_bytes, "application/pdf")}
        up_res = await client.post("/api/documents/upload", files=files)
        doc_id = up_res.json()["document"]["id"]
        await client.post(f"/api/documents/{doc_id}/process")

        # Get Page 2 specifically
        page2_res = await client.get(f"/api/documents/{doc_id}/pages/2")
        assert page2_res.status_code == 200
        p2 = page2_res.json()
        assert p2["page_number"] == 2
        assert "DoorStatus_If" in p2["cleaned_text"]

        # Get non-existent page 99
        page99_res = await client.get(f"/api/documents/{doc_id}/pages/99")
        assert page99_res.status_code == 404
