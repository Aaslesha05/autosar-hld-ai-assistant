"""
query.py
--------
RAG architectural question answering endpoint.
POST /api/query
"""

import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from app.rag.rag_service import get_rag_service

router = APIRouter(prefix="/query", tags=["RAG Query Engine"])
logger = logging.getLogger("autosar_hld_query_api")

@router.post("", response_model=RAGQueryResponse)
async def query_architecture(request: RAGQueryRequest):
    """
    Execute grounded RAG question answering on ingested AUTOSAR HLD documents.
    Returns:
    - Grounded LLM answer
    - Traceable source citations with page numbers and sections
    - Retrieved evidence chunks
    - Retrieval confidence score and level
    - Architectural limitations
    """
    rag_service = get_rag_service()
    try:
        response = await rag_service.answer_query(request)
        return response
    except Exception as e:
        logger.error(f"Error processing RAG query: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )
