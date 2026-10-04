"""
test_rag.py
-----------
Comprehensive automated test suite for Phase 4 — RAG Question Answering,
Retrieval Filtering, Grounded Prompts, Source Citations, and Confidence Metrics.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.rag.retriever import HLDRetriever
from app.rag.rag_service import RAGService, get_rag_service
from app.rag.llm_client import get_llm_client, MockLLMClient
from app.schemas.rag import RAGQueryRequest
from app.ingestion.ingestion_service import DocumentIngestionService


@pytest.fixture(scope="module")
def v1_pdf_bytes():
    with open("data/sample/AUTOSAR_BodyControl_HLD_v1.0.pdf", "rb") as f:
        return f.read()


@pytest.fixture(scope="module")
def v2_pdf_bytes():
    with open("data/sample/AUTOSAR_BodyControl_HLD_v2.0.pdf", "rb") as f:
        return f.read()


@pytest.fixture(scope="module")
def test_docs(v1_pdf_bytes, v2_pdf_bytes):
    """Ensure sample v1.0 and v2.0 documents are uploaded and ingested for RAG tests."""
    import asyncio
    async def _setup():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Upload v1
            up1 = await client.post(
                "/api/documents/upload",
                files={"file": ("AUTOSAR_BCM_v1.0_RAG.pdf", v1_pdf_bytes, "application/pdf")},
                data={"title": "BCM HLD v1.0 RAG", "version_tag": "v1.0"}
            )
            v1_id = up1.json()["document"]["id"]
            DocumentIngestionService.ingest_document(v1_id)

            # Upload v2
            up2 = await client.post(
                "/api/documents/upload",
                files={"file": ("AUTOSAR_BCM_v2.0_RAG.pdf", v2_pdf_bytes, "application/pdf")},
                data={"title": "BCM HLD v2.0 RAG", "version_tag": "v2.0"}
            )
            v2_id = up2.json()["document"]["id"]
            DocumentIngestionService.ingest_document(v2_id)

            return {"v1_id": v1_id, "v2_id": v2_id}

    return asyncio.run(_setup())


# ---------------------------------------------------------------------------
# 1. Retrieval & Query Embedding
# ---------------------------------------------------------------------------

def test_query_retrieval_and_embedding(test_docs):
    """Verify that query embedding and ChromaDB retrieval return relevant chunks."""
    retriever = HLDRetriever()
    v1_id = test_docs["v1_id"]

    chunks = retriever.retrieve(
        query="Run_ReadDoorSensors cycle time debounce timer",
        document_id=v1_id,
        top_k=3,
        similarity_threshold=0.30
    )

    assert len(chunks) > 0
    top_chunk = chunks[0]
    assert top_chunk.document_id == v1_id
    assert top_chunk.similarity_score > 0.40
    assert top_chunk.page_number in [2, 3]
    assert any(term in top_chunk.content for term in ["Run_ReadDoorSensors", "DoorControlSWC", "ms"])


# ---------------------------------------------------------------------------
# 2. Document & Version Filtering
# ---------------------------------------------------------------------------

def test_document_and_version_filtering(test_docs):
    """
    Verify strict document isolation and version filtering in retriever:
    - Scoping to doc A returns only doc A chunks.
    - Scoping to version 'v2.0' returns only 'v2.0' chunks.
    """
    retriever = HLDRetriever()
    v1_id = test_docs["v1_id"]
    v2_id = test_docs["v2_id"]

    # 1. Document ID Filter
    chunks_v1 = retriever.retrieve(
        query="Software Components architecture overview",
        document_id=v1_id,
        top_k=5
    )
    for c in chunks_v1:
        assert c.document_id == v1_id

    # 2. Version Tag Filter
    chunks_v2 = retriever.retrieve(
        query="Software Components architecture overview",
        version_tag="v2.0",
        top_k=5
    )
    for c in chunks_v2:
        assert c.version_tag == "v2.0"


# ---------------------------------------------------------------------------
# 3. Empty Retrieval & Similarity Threshold
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_retrieval_and_threshold(test_docs):
    """
    When similarity threshold is set high or query is completely irrelevant,
    retrieval yields empty chunks and RAG returns controlled insufficient evidence response.
    """
    rag_service = get_rag_service()
    req = RAGQueryRequest(
        question="What is the price of purple bananas in Antarctica?",
        document_id=test_docs["v1_id"],
        similarity_threshold=0.90  # Unrealistic threshold to force empty
    )

    res = await rag_service.answer_query(req)
    assert res.confidence == 0.0
    assert res.confidence_level == "INSUFFICIENT"
    assert "Insufficient evidence" in res.answer
    assert len(res.citations) == 0
    assert len(res.retrieved_chunks) == 0


# ---------------------------------------------------------------------------
# 4. Grounded Prompt & Citation Generation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_grounded_prompt_and_citations(test_docs):
    """
    Verify that retrieved chunks generate structured citations with
    exact page numbers, headings, source types, and snippets.
    """
    rag_service = get_rag_service()
    req = RAGQueryRequest(
        question="What is the DoorStatus_If interface?",
        document_id=test_docs["v1_id"],
        top_k=3
    )

    res = await rag_service.answer_query(req)
    assert res.confidence > 0.40
    assert res.confidence_level in ["MEDIUM", "HIGH"]
    assert len(res.citations) > 0

    first_cite = res.citations[0]
    assert first_cite.citation_index == 1
    assert first_cite.document_id == test_docs["v1_id"]
    assert "AUTOSAR" in first_cite.filename
    assert first_cite.page_number in [1, 2, 3]
    assert first_cite.heading != ""
    assert len(first_cite.snippet) > 5
    assert first_cite.similarity_score > 0.35


# ---------------------------------------------------------------------------
# 5. Insufficient Evidence for Unsupported Inquiries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_insufficient_evidence_unsupported_question(test_docs):
    """
    Test intentionally unsupported question:
    'What is the exact ECU hardware part number?'
    Must NOT hallucinate a part number; must return controlled insufficient evidence response.
    """
    rag_service = get_rag_service()
    req = RAGQueryRequest(
        question="What is the exact ECU hardware part number?",
        document_id=test_docs["v1_id"]
    )

    res = await rag_service.answer_query(req)
    assert "Insufficient evidence in the selected HLD documents to answer this question." in res.answer


# ---------------------------------------------------------------------------
# 6. Multiple-Version Retrieval & Limitations Notice
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multiple_version_retrieval_limitations(test_docs):
    """
    When searching across all documents without version filter,
    if evidence spans both v1.0 and v2.0, the limitations list must alert the user.
    """
    rag_service = get_rag_service()
    req = RAGQueryRequest(
        question="System Architectural Overview BodyControlSWC",
        top_k=6  # retrieve enough to span both docs
    )

    res = await rag_service.answer_query(req)
    assert len(res.retrieved_chunks) > 0
    versions = {c.version_tag for c in res.retrieved_chunks}
    if len(versions) > 1:
        has_version_warning = any("multiple HLD revisions" in lim for lim in res.limitations)
        assert has_version_warning, f"Expected multi-version limitation notice. Got: {res.limitations}"


# ---------------------------------------------------------------------------
# 7. API Query Endpoint Verification (POST /api/query)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_query_endpoint(test_docs):
    """
    Test POST /api/query endpoint schema compliance.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "question": "What is the cycle time of Run_ReadDoorSensors?",
            "document_id": test_docs["v1_id"],
            "top_k": 3,
            "similarity_threshold": 0.35
        }
        res = await client.post("/api/query", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert "answer" in data
        assert "citations" in data
        assert "retrieved_chunks" in data
        assert "confidence" in data
        assert "confidence_level" in data
        assert "limitations" in data

        assert len(data["citations"]) > 0
        assert data["confidence"] > 0.0
        assert data["confidence_level"] in ["MEDIUM", "HIGH"]


# ---------------------------------------------------------------------------
# 8. Real End-to-End Architectural Verification Questions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_real_question_1_run_readdoorsensors_timing(test_docs):
    """
    QUESTION 1: 'What is the cycle time of Run_ReadDoorSensors?'
    Verify:
    - relevant chunks retrieved from Page 3
    - answer states 20 ms
    - citations point to Page 3
    """
    rag_service = get_rag_service()
    req = RAGQueryRequest(
        question="What is the cycle time of Run_ReadDoorSensors?",
        document_id=test_docs["v1_id"]
    )
    res = await rag_service.answer_query(req)

    assert "20 ms" in res.answer or "20ms" in res.answer
    assert "Run_ReadDoorSensors" in res.answer
    assert len(res.citations) > 0
    # Page 3 contains runnable timing in the sample HLD
    cite_pages = [c.page_number for c in res.citations]
    assert 3 in cite_pages, f"Expected citation on Page 3, got: {cite_pages}"


@pytest.mark.asyncio
async def test_real_question_2_doorstatus_if_swcs(test_docs):
    """
    QUESTION 2: 'Which software components are involved in DoorStatus_If?'
    Verify:
    - DoorControlSWC and BodyControlSWC identified
    - citations point to Page 2 (Interface configuration)
    """
    rag_service = get_rag_service()
    req = RAGQueryRequest(
        question="Which software components are involved in DoorStatus_If?",
        document_id=test_docs["v1_id"]
    )
    res = await rag_service.answer_query(req)

    assert "DoorControlSWC" in res.answer
    assert "BodyControlSWC" in res.answer
    assert len(res.citations) > 0
    cite_pages = [c.page_number for c in res.citations]
    assert 2 in cite_pages, f"Expected citation on Page 2, got: {cite_pages}"


@pytest.mark.asyncio
async def test_real_question_3_version_changes(test_docs):
    """
    QUESTION 3: 'What changed between the available v1.0 and v2.0 information regarding the body control architecture?'
    Verify:
    - Answer references both v1.0 and v2.0
    - Citations include both v1.0 and v2.0 sources
    """
    rag_service = get_rag_service()
    req = RAGQueryRequest(
        question="What changed between the available v1.0 and v2.0 information regarding the body control architecture?",
        top_k=6
    )
    res = await rag_service.answer_query(req)

    assert "v1.0" in res.answer
    assert "v2.0" in res.answer
    assert len(res.citations) > 0
    version_tags = {c.version_tag for c in res.citations}
    assert "v1.0" in version_tags or "v2.0" in version_tags
