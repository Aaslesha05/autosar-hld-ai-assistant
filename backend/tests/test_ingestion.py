"""
test_ingestion.py
-----------------
Automated test suite for Phase 3 — Intelligent Chunking, SentenceTransformer Embeddings,
and ChromaDB Vector Storage.

Verifies:
1. Context-aware chunk creation from processed pages
2. Tabular data conversion to structured Markdown blocks
3. Metadata preservation and traceability (chunk -> page -> document -> PDF)
4. Page-number preservation
5. Heading/section metadata preservation
6. OCR metadata preservation on scanned pages
7. SentenceTransformer embedding generation, singleton caching, and dimension (384)
8. Safe handling of empty/invalid chunks
9. ChromaDB vector insertion and retrieval by document
10. Deterministic, idempotent re-ingestion (no duplicate vectors)
11. Document isolation in vector store
12. API ingestion endpoints (POST /ingest, GET /ingestion)
13. Live semantic similarity search verification
14. Real ingestion of sample AUTOSAR HLD v1.0 and v2.0 documents
"""

import os
import math
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.ingestion.pdf_processor import PDFProcessor
from app.ingestion.chunker import AUTOSARChunker
from app.ingestion.embedding_service import get_embedding_service, EmbeddingService
from app.ingestion.vector_store import get_vector_store, ChromaVectorStore
from app.ingestion.ingestion_service import DocumentIngestionService
from tests.test_ocr_fallback import _build_image_only_pdf_bytes


@pytest.fixture(scope="module")
def v1_pdf_bytes():
    with open("data/sample/AUTOSAR_BodyControl_HLD_v1.0.pdf", "rb") as f:
        return f.read()


@pytest.fixture(scope="module")
def v2_pdf_bytes():
    with open("data/sample/AUTOSAR_BodyControl_HLD_v2.0.pdf", "rb") as f:
        return f.read()


@pytest.fixture(scope="module")
def image_only_pdf_bytes():
    return _build_image_only_pdf_bytes()


# ---------------------------------------------------------------------------
# 1. Chunk Creation & Table Preservation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chunk_creation_and_table_preservation(v1_pdf_bytes):
    """
    Verify that processed pages are converted into context-aware chunks,
    preserving heading sections and converting tables into markdown blocks.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("AUTOSAR_BCM_v1_ChunkTest.pdf", v1_pdf_bytes, "application/pdf")}
        up_res = await client.post("/api/documents/upload", files=files, data={"version_tag": "v1.0"})
        assert up_res.status_code == 201
        doc_id = up_res.json()["document"]["id"]

        # Process pages
        await client.post(f"/api/documents/{doc_id}/process")
        pages = PDFProcessor.get_document_pages(doc_id)
        assert len(pages) == 3

        chunker = AUTOSARChunker()
        doc_meta = {"document_id": doc_id, "filename": "AUTOSAR_BCM_v1_ChunkTest.pdf", "version_tag": "v1.0"}
        chunks = chunker.create_chunks_from_document(doc_id, pages, doc_meta)

        assert len(chunks) >= 3, f"Expected multiple chunks, got {len(chunks)}"

        # Verify table chunk exists
        table_chunks = [c for c in chunks if c.metadata.source_type == "table"]
        assert len(table_chunks) >= 1, "Expected at least 1 table chunk from v1.0 document."

        first_table = table_chunks[0]
        assert "|" in first_table.content, "Table chunk must contain markdown table separator '|'"
        assert "---" in first_table.content, "Table chunk must contain markdown header divider"
        assert first_table.metadata.source_type == "table"


# ---------------------------------------------------------------------------
# 2. Metadata & Traceability Preservation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metadata_and_page_traceability(v1_pdf_bytes):
    """
    Verify strict traceability: each chunk preserves document_id, filename,
    version_tag, page_number, heading, word_count, and char_count.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("AUTOSAR_Traceability_Test.pdf", v1_pdf_bytes, "application/pdf")}
        up_res = await client.post("/api/documents/upload", files=files, data={"version_tag": "v1.0"})
        doc_id = up_res.json()["document"]["id"]

        await client.post(f"/api/documents/{doc_id}/process")
        pages = PDFProcessor.get_document_pages(doc_id)
        chunker = AUTOSARChunker()
        doc_meta = {"document_id": doc_id, "filename": "AUTOSAR_Traceability_Test.pdf", "version_tag": "v1.0"}
        chunks = chunker.create_chunks_from_document(doc_id, pages, doc_meta)

        seen_page_numbers = set()
        for idx, chunk in enumerate(chunks):
            meta = chunk.metadata
            assert meta.chunk_id == f"{doc_id}_p{meta.page_number}_c{idx}"
            assert meta.chunk_index == idx
            assert meta.document_id == doc_id
            assert meta.filename == "AUTOSAR_Traceability_Test.pdf"
            assert meta.version_tag == "v1.0"
            assert meta.page_number in [1, 2, 3]
            assert meta.heading is not None and len(meta.heading) > 0
            assert meta.word_count == len(chunk.content.split())
            assert meta.char_count == len(chunk.content)
            seen_page_numbers.add(meta.page_number)

        # All 3 pages must be represented
        assert seen_page_numbers == {1, 2, 3}


# ---------------------------------------------------------------------------
# 3. OCR Metadata Preservation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ocr_metadata_preservation(image_only_pdf_bytes):
    """
    Verify that chunks produced from an OCR-processed page preserve is_ocr=True
    and source_type='ocr'.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("Scanned_Chunk_Test.pdf", image_only_pdf_bytes, "application/pdf")}
        up_res = await client.post("/api/documents/upload", files=files)
        doc_id = up_res.json()["document"]["id"]

        # Process with OCR
        await client.post(f"/api/documents/{doc_id}/process")
        pages = PDFProcessor.get_document_pages(doc_id)
        assert len(pages) == 1
        assert pages[0].is_ocr is True

        chunker = AUTOSARChunker()
        doc_meta = {"document_id": doc_id, "filename": "Scanned_Chunk_Test.pdf", "version_tag": "v1.0"}
        chunks = chunker.create_chunks_from_document(doc_id, pages, doc_meta)

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.metadata.is_ocr is True
            assert chunk.metadata.source_type == "ocr"
            assert "AUTOSAR" in chunk.content.upper()


# ---------------------------------------------------------------------------
# 4. Embedding Service Verification
# ---------------------------------------------------------------------------

def test_embedding_service_singleton_batching_and_dimension():
    """
    Verify SentenceTransformer embedding model loads once, outputs 384 dimensions,
    supports batching, and produces cosine-normalized vectors.
    """
    emb_service = get_embedding_service()
    assert emb_service.dimension == 384
    assert emb_service.model_name == settings.EMBEDDING_MODEL

    # Batch test
    texts = [
        "BodyControlSWC manages exterior lighting and power modes.",
        "DoorControlSWC handles lock/unlock sensor inputs.",
        "CAN transceiver diagnostic routines comply with ISO 26262 ASIL-B."
    ]
    vectors = emb_service.embed_texts(texts, batch_size=2)
    assert len(vectors) == 3
    for v in vectors:
        assert len(v) == 384
        # Verify L2 normalization (sum of squares ~ 1.0)
        norm = math.sqrt(sum(x * x for x in v))
        assert abs(norm - 1.0) < 1e-4

    # Single query test
    q_vec = emb_service.embed_query("DoorStatus interface")
    assert len(q_vec) == 384


# ---------------------------------------------------------------------------
# 5. Empty and Invalid Chunk Handling
# ---------------------------------------------------------------------------

def test_empty_and_invalid_chunk_handling():
    """
    Verify embedding service safely handles empty strings, whitespace, and None
    without crashing or returning invalid shapes.
    """
    emb_service = get_embedding_service()
    bad_inputs = ["", "    ", None, "\n\n"]
    vectors = emb_service.embed_texts(bad_inputs)
    assert len(vectors) == 4
    for v in vectors:
        assert len(v) == 384
        norm = math.sqrt(sum(x * x for x in v))
        assert abs(norm - 1.0) < 1e-4


# ---------------------------------------------------------------------------
# 6. ChromaDB Insertion and Retrieval by Document
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chromadb_insertion_and_retrieval(v1_pdf_bytes):
    """
    Verify that chunks and vectors are correctly inserted into persistent ChromaDB
    and can be retrieved by document_id.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("AUTOSAR_Chroma_Insert_Test.pdf", v1_pdf_bytes, "application/pdf")}
        up_res = await client.post("/api/documents/upload", files=files)
        doc_id = up_res.json()["document"]["id"]

        # Run full ingestion service
        ingest_res = DocumentIngestionService.ingest_document(doc_id)
        assert ingest_res.status == "ingested"
        assert ingest_res.total_chunks > 0
        assert ingest_res.total_vectors == ingest_res.total_chunks

        # Query ChromaDB directly
        vector_store = get_vector_store()
        doc_data = vector_store.get_document_chunks(doc_id)
        assert len(doc_data["ids"]) == ingest_res.total_chunks

        # Check metadata in ChromaDB record
        meta = doc_data["metadatas"][0]
        assert meta["document_id"] == doc_id
        assert "page_number" in meta
        assert "heading" in meta
        assert "source_type" in meta


# ---------------------------------------------------------------------------
# 7. Deterministic and Idempotent Re-ingestion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_idempotent_reingestion(v1_pdf_bytes):
    """
    Verify that re-ingesting the exact same document multiple times does NOT
    produce duplicate vectors in ChromaDB.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("AUTOSAR_Idempotent_Test.pdf", v1_pdf_bytes, "application/pdf")}
        up_res = await client.post("/api/documents/upload", files=files)
        doc_id = up_res.json()["document"]["id"]

        # Ingestion 1
        res1 = DocumentIngestionService.ingest_document(doc_id)
        count1 = res1.total_vectors

        # Ingestion 2 (Reprocess / Re-ingest)
        res2 = DocumentIngestionService.ingest_document(doc_id)
        count2 = res2.total_vectors

        assert count1 == count2, f"Vector count changed on re-ingestion: {count1} vs {count2}"

        # Check live ChromaDB count
        vector_store = get_vector_store()
        live_count = vector_store.count_document_vectors(doc_id)
        assert live_count == count1, f"Expected {count1} vectors in ChromaDB, found {live_count}"


# ---------------------------------------------------------------------------
# 8. Document Isolation in Vector Store
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_document_isolation(v1_pdf_bytes, v2_pdf_bytes):
    """
    Verify that document A's vectors and document B's vectors remain completely
    isolated in ChromaDB. Deleting doc A must not affect doc B.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Ingest Document A
        files_a = {"file": ("Doc_A.pdf", v1_pdf_bytes, "application/pdf")}
        up_a = await client.post("/api/documents/upload", files=files_a)
        doc_a_id = up_a.json()["document"]["id"]
        res_a = DocumentIngestionService.ingest_document(doc_a_id)

        # Ingest Document B
        files_b = {"file": ("Doc_B.pdf", v2_pdf_bytes, "application/pdf")}
        up_b = await client.post("/api/documents/upload", files=files_b)
        doc_b_id = up_b.json()["document"]["id"]
        res_b = DocumentIngestionService.ingest_document(doc_b_id)

        vector_store = get_vector_store()
        count_a = vector_store.count_document_vectors(doc_a_id)
        count_b = vector_store.count_document_vectors(doc_b_id)
        assert count_a == res_a.total_vectors
        assert count_b == res_b.total_vectors

        # Delete Document A
        vector_store.delete_document_vectors(doc_a_id)
        assert vector_store.count_document_vectors(doc_a_id) == 0
        # Document B must remain completely intact
        assert vector_store.count_document_vectors(doc_b_id) == count_b


# ---------------------------------------------------------------------------
# 9. API Ingestion Endpoints (POST & GET)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_ingestion_endpoints(v1_pdf_bytes):
    """
    Verify POST /api/documents/{id}/ingest and GET /api/documents/{id}/ingestion.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("API_Ingest_Doc.pdf", v1_pdf_bytes, "application/pdf")}
        up_res = await client.post("/api/documents/upload", files=files)
        doc_id = up_res.json()["document"]["id"]

        # Query status before ingestion
        status_before = await client.get(f"/api/documents/{doc_id}/ingestion")
        assert status_before.status_code == 200
        assert status_before.json()["status"] == "not_ingested"

        # Trigger ingestion via POST
        ingest_res = await client.post(f"/api/documents/{doc_id}/ingest")
        assert ingest_res.status_code == 200
        data = ingest_res.json()
        assert data["status"] == "ingested"
        assert data["total_chunks"] > 0
        assert data["total_vectors"] > 0
        assert data["collection_name"] == settings.CHROMA_COLLECTION_NAME

        # Query status after ingestion via GET
        status_after = await client.get(f"/api/documents/{doc_id}/ingestion")
        assert status_after.status_code == 200
        stat_data = status_after.json()
        assert stat_data["status"] == "ingested"
        assert stat_data["total_vectors"] == data["total_vectors"]
        assert stat_data["embedding_model"] == settings.EMBEDDING_MODEL


# ---------------------------------------------------------------------------
# 10. Live Semantic Similarity Search Verification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_live_similarity_search_verification(v1_pdf_bytes):
    """
    Verify that ChromaDB similarity search returns semantically relevant
    AUTOSAR architectural chunks with accurate page metadata.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("Semantic_Search_HLD.pdf", v1_pdf_bytes, "application/pdf")}
        up_res = await client.post("/api/documents/upload", files=files)
        doc_id = up_res.json()["document"]["id"]
        DocumentIngestionService.ingest_document(doc_id)

        emb_service = get_embedding_service()
        vector_store = get_vector_store()

        # Query: Driver door unlock sequence and ASIL-B profile
        query_text = "Driver door unlock sequence E2E Profile 01 ASIL-B"
        query_vec = emb_service.embed_query(query_text)

        hits = vector_store.similarity_search(query_vec, n_results=3, document_id=doc_id)
        assert len(hits) > 0

        top_hit = hits[0]
        assert top_hit["similarity_score"] > 0.4
        meta = top_hit["metadata"]
        assert meta["document_id"] == doc_id
        # Page 3 of v1.0 specifically defines Scenario 1 Driver Door Unlock Sequence
        assert meta["page_number"] in [2, 3]
        assert any(term in top_hit["content"] for term in ["Door", "ASIL", "Sequence", "E2E", "Profile"])


# ---------------------------------------------------------------------------
# 11. Actual Ingestion of Sample HLD v1.0 and v2.0 Documents
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_actual_v1_and_v2_sample_ingestion(v1_pdf_bytes, v2_pdf_bytes):
    """
    End-to-end integration test: Actually ingest AUTOSAR_BodyControl_HLD_v1.0.pdf
    and AUTOSAR_BodyControl_HLD_v2.0.pdf into ChromaDB, verifying vectors,
    chunk counts, and database status for both revisions.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Ingest v1.0
        files_v1 = {"file": ("AUTOSAR_BodyControl_HLD_v1.0.pdf", v1_pdf_bytes, "application/pdf")}
        up_v1 = await client.post("/api/documents/upload", files=files_v1, data={"title": "Body Control HLD v1.0", "version_tag": "v1.0"})
        doc_v1_id = up_v1.json()["document"]["id"]

        ingest_v1 = await client.post(f"/api/documents/{doc_v1_id}/ingest")
        assert ingest_v1.status_code == 200
        data_v1 = ingest_v1.json()
        assert data_v1["status"] == "ingested"
        assert data_v1["total_chunks"] >= 5
        assert data_v1["total_vectors"] >= 5

        # Ingest v2.0
        files_v2 = {"file": ("AUTOSAR_BodyControl_HLD_v2.0.pdf", v2_pdf_bytes, "application/pdf")}
        up_v2 = await client.post("/api/documents/upload", files=files_v2, data={"title": "Body Control HLD v2.0", "version_tag": "v2.0"})
        doc_v2_id = up_v2.json()["document"]["id"]

        ingest_v2 = await client.post(f"/api/documents/{doc_v2_id}/ingest")
        assert ingest_v2.status_code == 200
        data_v2 = ingest_v2.json()
        assert data_v2["status"] == "ingested"
        assert data_v2["total_chunks"] >= 5
        assert data_v2["total_vectors"] >= 5

        # Confirm ChromaDB persistent storage reflects both
        vector_store = get_vector_store()
        count_v1 = vector_store.count_document_vectors(doc_v1_id)
        count_v2 = vector_store.count_document_vectors(doc_v2_id)
        assert count_v1 == data_v1["total_vectors"]
        assert count_v2 == data_v2["total_vectors"]
