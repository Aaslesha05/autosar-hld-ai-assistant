import asyncio
import sys
import os

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rag import get_rag_service
from app.schemas.rag import RAGQueryRequest

async def run_verification():
    rag = get_rag_service()
    
    questions = [
        "What is the cycle time of Run_ReadDoorSensors?",
        "Which software components are involved in DoorStatus_If?",
        "What changed between the available v1.0 and v2.0 information regarding the body control architecture?",
        "What is the exact ECU hardware part number?"
    ]
    
    for i, q in enumerate(questions, 1):
        print(f"=== QUESTION {i}: {q} ===")
        req = RAGQueryRequest(question=q, top_k=4)
        res = await rag.answer_query(req)
        print(f"Answer:\n{res.answer}\n")
        print(f"Confidence: {res.confidence:.4f} ({res.confidence_level})")
        print(f"Limitations: {res.limitations}")
        print(f"Citations ({len(res.citations)}):")
        for c in res.citations:
            print(f"  [#{c.citation_index}] Doc: {c.filename} | Version: {c.version_tag} | Page: {c.page_number} | Section: {c.heading} | Score: {c.similarity_score:.4f}")
            print(f"       Snippet: {c.snippet[:120]}...")
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(run_verification())
