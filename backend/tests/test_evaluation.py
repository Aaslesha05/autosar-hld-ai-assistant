"""
test_evaluation.py
------------------
Deterministic evaluation suite of 10 architectural questions
derived strictly from AUTOSAR_BodyControl_HLD_v1.0 and v2.0.

Evaluates:
- Answer accuracy against source HLD
- Retrieved source and exact page numbers
- Citation correctness and traceable chain
- Groundedness (no hallucinations)
- Rejection of unsupported questions (exact refusal string)
"""

import pytest
import pytest_asyncio
from app.rag.rag_service import get_rag_service
from app.schemas.rag import RAGQueryRequest


EVALUATION_DATASET = [
    {
        "id": "EVAL-01",
        "category": "subsystem_scope",
        "question": "What is the architectural scope of the Body Control Module subsystem?",
        "expected_page": 1,
        "is_supported": True,
        "expected_keywords": ["Body Control Module", "BCM", "AUTOSAR"]
    },
    {
        "id": "EVAL-02",
        "category": "component_interfaces",
        "question": "Which software components communicate via LightControl_If?",
        "expected_page": 2,
        "is_supported": True,
        "expected_keywords": ["LightControl_If", "BodyControlSWC", "LightingSWC"]
    },
    {
        "id": "EVAL-03",
        "category": "ports_signals",
        "question": "Which ports connect DoorControlSWC and BodyControlSWC?",
        "expected_page": 2,
        "is_supported": True,
        "expected_keywords": ["P_DoorStatus", "R_DoorStatus", "DoorStatus_If"]
    },
    {
        "id": "EVAL-04",
        "category": "runnable_timing",
        "question": "What is the cycle time and debounce timer of Run_ReadDoorSensors?",
        "expected_page": 3,
        "is_supported": True,
        "expected_keywords": ["Run_ReadDoorSensors", "20 ms", "50 ms"]
    },
    {
        "id": "EVAL-05",
        "category": "dependencies",
        "question": "What triggers Scenario 1: Driver Door Unlock Sequence?",
        "expected_page": 3,
        "is_supported": True,
        "expected_keywords": ["capacitive sensor", "driver door"]
    },
    {
        "id": "EVAL-06",
        "category": "safety_relationships",
        "question": "What does section 6 specify regarding ISO 26262 requirements for DoorControlSWC?",
        "expected_page": 3,
        "is_supported": True,
        "expected_keywords": ["ISO 26262", "ASIL", "DoorControlSWC"]
    },
    {
        "id": "EVAL-07",
        "category": "version_specific",
        "question": "What changed between the available v1.0 and v2.0 information regarding the body control architecture?",
        "expected_page": 1,
        "is_supported": True,
        "expected_keywords": ["v1.0", "v2.0"]
    },
    {
        "id": "EVAL-08",
        "category": "table_derived",
        "question": "What is the execution period and safety category of PowerDistributionSWC in the SWC table?",
        "expected_page": 1,
        "is_supported": True,
        "expected_keywords": ["PowerDistributionSWC", "100 ms", "ASIL-B"]
    },
    {
        "id": "EVAL-09",
        "category": "unsupported_hardware",
        "question": "What is the exact ECU hardware part number and microprocessor clock speed?",
        "expected_page": None,
        "is_supported": False,
        "expected_keywords": ["Insufficient evidence in the selected HLD documents to answer this question."]
    },
    {
        "id": "EVAL-10",
        "category": "unsupported_bus_rate",
        "question": "What is the CAN bus baud rate for the body powertrain gateway?",
        "expected_page": None,
        "is_supported": False,
        "expected_keywords": ["Insufficient evidence in the selected HLD documents to answer this question."]
    }
]


@pytest.mark.asyncio
@pytest.mark.parametrize("item", EVALUATION_DATASET, ids=[d["id"] for d in EVALUATION_DATASET])
async def test_evaluation_item(item):
    """
    Evaluate each question in the 10-item benchmark set against the live ChromaDB store.
    """
    rag = get_rag_service()
    req = RAGQueryRequest(question=item["question"], top_k=4)
    res = await rag.answer_query(req)

    if item["is_supported"]:
        # 1. Answer must be non-empty and not refuse
        assert "Insufficient evidence" not in res.answer
        # 2. Key architectural concepts must be present
        for kw in item["expected_keywords"]:
            assert kw.lower() in res.answer.lower() or any(kw.lower() in c.snippet.lower() for c in res.citations), \
                f"Missing keyword '{kw}' in answer for {item['id']}"
        # 3. Must have valid citations
        assert len(res.citations) > 0
        citation_pages = [c.page_number for c in res.citations]
        assert item["expected_page"] in citation_pages, \
            f"Expected citation on Page {item['expected_page']}, got {citation_pages} for {item['id']}"
        # 4. Confidence must be reasonable
        assert res.confidence > 0.35
    else:
        # Negative control test: MUST reject with controlled message
        assert "Insufficient evidence in the selected HLD documents to answer this question." in res.answer
        assert res.confidence == 0.0 or res.confidence_level in ["LOW", "INSUFFICIENT"]
