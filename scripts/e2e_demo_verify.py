"""
scripts/e2e_demo_verify.py
--------------------------
End-to-End Clean Workflow Verification:
1. Initialize clean SQLite & ChromaDB state for official sample HLDs.
2. Ingest AUTOSAR_BodyControl_HLD_v1.0.pdf (Upload -> Process -> Ingest via HTTP API).
3. Ingest AUTOSAR_BodyControl_HLD_v2.0.pdf (Upload -> Process -> Ingest via HTTP API).
4. Verify exact chunk counts (25 for v1.0, 32 for v2.0 -> total 57 vectors).
5. Run the 10-question evaluation benchmark and calculate exact real metrics.
"""

import sys
import os
import asyncio
from httpx import AsyncClient, ASGITransport

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.main import app
from app.core.config import settings
from app.core.database import init_db, get_connection
from app.ingestion.vector_store import get_vector_store


async def run_clean_e2e_verification():
    print("=" * 65)
    print("AUTOSAR HLD AI ASSISTANT — CLEAN END-TO-END PIPELINE VERIFICATION")
    print("=" * 65)

    v1_pdf = os.path.join(settings.SAMPLE_DIR, "AUTOSAR_BodyControl_HLD_v1.0.pdf")
    v2_pdf = os.path.join(settings.SAMPLE_DIR, "AUTOSAR_BodyControl_HLD_v2.0.pdf")

    assert os.path.exists(v1_pdf), f"Sample v1.0 missing at {v1_pdf}"
    assert os.path.exists(v2_pdf), f"Sample v2.0 missing at {v2_pdf}"

    # 1. Clean ChromaDB collection to isolate official sample data
    vs = get_vector_store()
    try:
        vs.client.delete_collection(settings.CHROMA_COLLECTION_NAME)
    except Exception:
        pass
    vs.collection = vs.client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION_NAME,
        embedding_function=None,
        metadata={"hnsw:space": "cosine"}
    )
    print(f"[1/5] Initialized clean ChromaDB collection '{settings.CHROMA_COLLECTION_NAME}'. Vector count: {vs.collection.count()}")

    # 2. Clean SQLite database
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM document_ingestions")
        conn.execute("DELETE FROM document_pages")
        conn.execute("DELETE FROM documents")
        conn.commit()
    print("[2/5] Initialized clean SQLite database tables.")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 3. Upload & Process & Ingest v1.0
        with open(v1_pdf, "rb") as f:
            v1_bytes = f.read()

        up_res_v1 = await client.post(
            "/api/documents/upload",
            files={"file": ("AUTOSAR_BodyControl_HLD_v1.0.pdf", v1_bytes, "application/pdf")},
            data={"title": "Body Control Module HLD Baseline", "version_tag": "v1.0"}
        )
        assert up_res_v1.status_code == 201, f"v1 upload failed: {up_res_v1.text}"
        v1_id = up_res_v1.json()["document"]["id"]
        print(f"[3/5] Uploaded v1.0 -> ID: {v1_id}")

        proc_res_v1 = await client.post(f"/api/documents/{v1_id}/process")
        assert proc_res_v1.status_code == 200, f"v1 process failed: {proc_res_v1.text}"
        print(f"      Processed v1.0 -> {proc_res_v1.json()['total_pages_processed']} pages, {proc_res_v1.json()['tables_found_count']} tables")

        ingest_res_v1 = await client.post(f"/api/documents/{v1_id}/ingest")
        assert ingest_res_v1.status_code == 200, f"v1 ingest failed: {ingest_res_v1.text}"
        v1_vecs = ingest_res_v1.json()["total_vectors"]
        print(f"      Ingested v1.0 -> {ingest_res_v1.json()['total_chunks']} chunks, {v1_vecs} vectors in ChromaDB")

        # 4. Upload & Process & Ingest v2.0
        with open(v2_pdf, "rb") as f:
            v2_bytes = f.read()

        up_res_v2 = await client.post(
            "/api/documents/upload",
            files={"file": ("AUTOSAR_BodyControl_HLD_v2.0.pdf", v2_bytes, "application/pdf")},
            data={"title": "Body Control Module HLD Updated", "version_tag": "v2.0"}
        )
        assert up_res_v2.status_code == 201, f"v2 upload failed: {up_res_v2.text}"
        v2_id = up_res_v2.json()["document"]["id"]
        print(f"[4/5] Uploaded v2.0 -> ID: {v2_id}")

        proc_res_v2 = await client.post(f"/api/documents/{v2_id}/process")
        assert proc_res_v2.status_code == 200, f"v2 process failed: {proc_res_v2.text}"
        print(f"      Processed v2.0 -> {proc_res_v2.json()['total_pages_processed']} pages, {proc_res_v2.json()['tables_found_count']} tables")

        ingest_res_v2 = await client.post(f"/api/documents/{v2_id}/ingest")
        assert ingest_res_v2.status_code == 200, f"v2 ingest failed: {ingest_res_v2.text}"
        v2_vecs = ingest_res_v2.json()["total_vectors"]
        print(f"      Ingested v2.0 -> {ingest_res_v2.json()['total_chunks']} chunks, {v2_vecs} vectors in ChromaDB")

        total_vectors = vs.collection.count()
        print(f"\n[SUMMARY] Total ChromaDB vectors: {total_vectors} (Expected: 57)")
        assert total_vectors == 57, f"Expected 57 vectors, got {total_vectors}"

        # 5. Run the 10 Evaluation Questions against the Clean Knowledge Base
        print("\n" + "=" * 65)
        print("RUNNING 10-QUESTION DETERMINISTIC RAG EVALUATION BENCHMARK")
        print("=" * 65)

        eval_dataset = [
            {
                "id": "EVAL-01",
                "category": "Subsystem Scope & Components",
                "question": "What is the architectural scope of the Body Control Module subsystem?",
                "expected_page": 1,
                "is_supported": True,
                "expected_keywords": ["Body Control Module", "BCM", "AUTOSAR"]
            },
            {
                "id": "EVAL-02",
                "category": "Component Interfaces",
                "question": "Which software components communicate via LightControl_If?",
                "expected_page": 2,
                "is_supported": True,
                "expected_keywords": ["LightControl_If", "BodyControlSWC", "LightingSWC"]
            },
            {
                "id": "EVAL-03",
                "category": "Ports & Connectors",
                "question": "Which ports connect DoorControlSWC and BodyControlSWC?",
                "expected_page": 2,
                "is_supported": True,
                "expected_keywords": ["P_DoorStatus", "R_DoorStatus", "DoorStatus_If"]
            },
            {
                "id": "EVAL-04",
                "category": "Runnable Timing",
                "question": "What is the cycle time and debounce timer of Run_ReadDoorSensors?",
                "expected_page": 3,
                "is_supported": True,
                "expected_keywords": ["Run_ReadDoorSensors", "20 ms", "50 ms"]
            },
            {
                "id": "EVAL-05",
                "category": "Functional Execution Flow",
                "question": "What triggers Scenario 1: Driver Door Unlock Sequence?",
                "expected_page": 3,
                "is_supported": True,
                "expected_keywords": ["capacitive sensor", "driver door"]
            },
            {
                "id": "EVAL-06",
                "category": "Safety & ISO 26262",
                "question": "What does section 6 specify regarding ISO 26262 requirements for DoorControlSWC?",
                "expected_page": 3,
                "is_supported": True,
                "expected_keywords": ["ISO 26262", "ASIL", "DoorControlSWC"]
            },
            {
                "id": "EVAL-07",
                "category": "Multi-Version Evolution",
                "question": "What changed between the available v1.0 and v2.0 information regarding the body control architecture?",
                "expected_page": 1,
                "is_supported": True,
                "expected_keywords": ["v1.0", "v2.0"]
            },
            {
                "id": "EVAL-08",
                "category": "Table-Derived Metrics",
                "question": "What is the execution period and safety category of PowerDistributionSWC in the SWC table?",
                "expected_page": 1,
                "is_supported": True,
                "expected_keywords": ["PowerDistributionSWC", "100 ms", "ASIL-B"]
            },
            {
                "id": "EVAL-09",
                "category": "Unsupported Hardware (Refusal)",
                "question": "What is the exact ECU hardware part number and microprocessor clock speed?",
                "expected_page": None,
                "is_supported": False,
                "expected_keywords": ["Insufficient evidence in the selected HLD documents to answer this question."]
            },
            {
                "id": "EVAL-10",
                "category": "Unsupported Bus Rate (Refusal)",
                "question": "What is the CAN bus baud rate for the body powertrain gateway?",
                "expected_page": None,
                "is_supported": False,
                "expected_keywords": ["Insufficient evidence in the selected HLD documents to answer this question."]
            }
        ]

        results = []
        passed_count = 0
        refusal_correct = 0
        citation_correct = 0

        for item in eval_dataset:
            query_payload = {
                "question": item["question"],
                "top_k": 4,
                "similarity_threshold": 0.35
            }
            res_raw = await client.post("/api/query", json=query_payload)
            assert res_raw.status_code == 200, f"Query failed: {res_raw.text}"
            res = res_raw.json()

            print(f"\n--- [{item['id']}] {item['category']} ---")
            print(f"Q: {item['question']}")
            print(f"A: {res['answer'][:140]}...")
            print(f"Confidence: {res['confidence']:.4f} ({res['confidence_level']})")
            print(f"Citations: {len(res['citations'])}")

            is_passed = True
            notes = []

            if item["is_supported"]:
                if "Insufficient evidence" in res["answer"]:
                    is_passed = False
                    notes.append("False refusal on supported question.")

                # Check citations
                cite_pages = [c["page_number"] for c in res["citations"]]
                if item["expected_page"] in cite_pages:
                    citation_correct += 1
                else:
                    is_passed = False
                    notes.append(f"Expected page {item['expected_page']} not in citations: {cite_pages}")

                # Check keywords in answer or citation snippets
                all_text = res["answer"] + " " + " ".join(c["snippet"] for c in res["citations"])
                for kw in item["expected_keywords"]:
                    if kw.lower() not in all_text.lower():
                        is_passed = False
                        notes.append(f"Missing keyword: '{kw}'")

            else:
                # Must refuse
                if "Insufficient evidence in the selected HLD documents to answer this question." in res["answer"]:
                    refusal_correct += 1
                else:
                    is_passed = False
                    notes.append("Failed to refuse unsupported inquiry.")

            if is_passed:
                passed_count += 1
                print("Status: [PASS]")
            else:
                print(f"Status: [FAIL] - {'; '.join(notes)}")

            results.append({
                "id": item["id"],
                "category": item["category"],
                "question": item["question"],
                "is_supported": item["is_supported"],
                "passed": is_passed,
                "citations": len(res["citations"]),
                "confidence": res["confidence"],
                "confidence_level": res["confidence_level"],
                "answer_preview": res["answer"][:140],
                "notes": notes
            })

        print("\n" + "=" * 65)
        print(f"BENCHMARK RESULTS: {passed_count}/{len(eval_dataset)} PASSED ({passed_count/len(eval_dataset)*100:.1f}%)")
        print(f"Supported Question Accuracy: {passed_count - refusal_correct}/8 ({(passed_count - refusal_correct)/8*100:.1f}%)")
        print(f"Citation Correctness: {citation_correct}/8 ({citation_correct/8*100:.1f}%)")
        print(f"Unsupported Question Refusal Rate: {refusal_correct}/2 ({refusal_correct/2*100:.1f}%)")
        print("=" * 65)

    return results

if __name__ == "__main__":
    asyncio.run(run_clean_e2e_verification())
