import io
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings

@pytest.fixture
def valid_pdf_bytes():
    with open("data/sample/AUTOSAR_BodyControl_HLD_v1.0.pdf", "rb") as f:
        return f.read()

@pytest.mark.asyncio
async def test_upload_valid_pdf(valid_pdf_bytes):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {
            "file": ("AUTOSAR_BCM_HLD.pdf", valid_pdf_bytes, "application/pdf")
        }
        data = {
            "title": "BCM High-Level Design",
            "version_tag": "v1.0"
        }
        response = await client.post("/api/documents/upload", files=files, data=data)
        assert response.status_code == 201
        res_data = response.json()
        assert "document" in res_data
        doc = res_data["document"]
        assert doc["filename"] == "AUTOSAR_BCM_HLD.pdf"
        assert doc["page_count"] > 0
        assert doc["status"] == "uploaded"
        assert doc["title"] == "BCM High-Level Design"
        assert doc["version_tag"] == "v1.0"
        assert len(doc["file_hash"]) == 64

@pytest.mark.asyncio
async def test_upload_invalid_extension():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {
            "file": ("malicious.txt", b"plain text content not a pdf", "text/plain")
        }
        response = await client.post("/api/documents/upload", files=files)
        assert response.status_code == 400
        assert "Only PDF files are supported" in response.json()["detail"]

@pytest.mark.asyncio
async def test_upload_fake_pdf_header():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {
            "file": ("fake.pdf", b"NOT_A_REAL_PDF_HEADER_JUST_BYTES_12345", "application/pdf")
        }
        response = await client.post("/api/documents/upload", files=files)
        assert response.status_code == 400
        assert "does not start with standard PDF header" in response.json()["detail"]

@pytest.mark.asyncio
async def test_upload_corrupted_pdf():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Starts with %PDF but has completely invalid binary garbage
        files = {
            "file": ("corrupt.pdf", b"%PDF-1.4\ncorrupted_garbage_bytes_without_xref_or_trailer", "application/pdf")
        }
        response = await client.post("/api/documents/upload", files=files)
        assert response.status_code == 400
        assert "Unable to parse PDF document structure" in response.json()["detail"]

@pytest.mark.asyncio
async def test_upload_oversized_file(monkeypatch):
    transport = ASGITransport(app=app)
    # Monkeypatch MAX_UPLOAD_SIZE_MB to 1 MB for testing
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        large_bytes = b"%PDF" + b"0" * (2 * 1024 * 1024)  # 2MB
        files = {
            "file": ("oversized.pdf", large_bytes, "application/pdf")
        }
        response = await client.post("/api/documents/upload", files=files)
        assert response.status_code == 413
        assert "exceeds maximum allowed limit" in response.json()["detail"]

@pytest.mark.asyncio
async def test_list_and_delete_documents(valid_pdf_bytes):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload a doc for lifecycle testing
        files = {"file": ("Lifecycle_Test.pdf", valid_pdf_bytes, "application/pdf")}
        up_res = await client.post("/api/documents/upload", files=files)
        doc_id = up_res.json()["document"]["id"]

        # 2. List documents
        list_res = await client.get("/api/documents")
        assert list_res.status_code == 200
        docs = list_res.json()["documents"]
        assert any(d["id"] == doc_id for d in docs)

        # 3. Get single document
        get_res = await client.get(f"/api/documents/{doc_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == doc_id

        # 4. Preview / download file
        file_res = await client.get(f"/api/documents/{doc_id}/file")
        assert file_res.status_code == 200
        assert file_res.headers["content-type"] == "application/pdf"

        # 5. Delete document
        del_res = await client.delete(f"/api/documents/{doc_id}")
        assert del_res.status_code == 200

        # 6. Verify 404 after deletion
        get_after = await client.get(f"/api/documents/{doc_id}")
        assert get_after.status_code == 404
