"""
rag_service.py
--------------
Main Phase 4 RAG service.
Coordinates:
User Question -> Query Embedding -> ChromaDB Retrieval -> Grounded Prompt Construction -> LLM Synthesis -> Source Citations.
"""

import logging
from typing import List, Dict, Any, Optional

from app.schemas.rag import (
    RAGQueryRequest,
    RAGQueryResponse,
    Citation,
    RetrievedChunk
)
from app.rag.retriever import HLDRetriever
from app.rag.llm_client import get_llm_client, GROUNDED_SYSTEM_PROMPT

logger = logging.getLogger("autosar_hld_rag_service")

class RAGService:
    def __init__(self):
        self.retriever = HLDRetriever()
        self.llm_client = get_llm_client()

    @classmethod
    def calculate_confidence(cls, chunks: List[RetrievedChunk]) -> tuple[float, str]:
        """
        Derive a transparent retrieval-based confidence indicator from similarity scores.
        Clearly labeled as retrieval confidence, not LLM probability certainty.
        """
        if not chunks:
            return 0.0, "INSUFFICIENT"

        top_score = chunks[0].similarity_score
        avg_score = sum(c.similarity_score for c in chunks) / len(chunks)
        confidence = round(0.6 * top_score + 0.4 * avg_score, 4)

        if confidence >= 0.65:
            level = "HIGH"
        elif confidence >= 0.48:
            level = "MEDIUM"
        else:
            level = "LOW"

        return confidence, level

    @classmethod
    def evaluate_limitations(cls, chunks: List[RetrievedChunk]) -> List[str]:
        """Generate architectural caveats and limitation notices based on retrieved evidence."""
        limitations: List[str] = []
        if not chunks:
            limitations.append("No relevant HLD chunks retrieved with similarity above threshold.")
            return limitations

        # Check for OCR-derived content
        ocr_count = sum(1 for c in chunks if c.is_ocr or c.source_type == "ocr")
        if ocr_count > 0:
            limitations.append(
                f"{ocr_count} of {len(chunks)} retrieved evidence chunks originate from scanned/OCR pages."
            )

        # Check for multi-version evidence
        versions = sorted(list({c.version_tag for c in chunks if c.version_tag}))
        if len(versions) > 1:
            limitations.append(
                f"Retrieved evidence spans multiple HLD revisions ({', '.join(versions)}); verify version-specific requirements."
            )

        # Check for marginal similarity
        if chunks[0].similarity_score < 0.50:
            limitations.append(
                "Top retrieval similarity score is relatively low; verify details against original documentation."
            )

        return limitations

    async def answer_query(self, request: RAGQueryRequest) -> RAGQueryResponse:
        """
        Execute full RAG pipeline with grounded generation and citation verification.
        """
        clean_q = request.question.strip()
        top_k = request.top_k or 5
        threshold = request.similarity_threshold if request.similarity_threshold is not None else 0.35

        # 1. Retrieve evidence chunks from ChromaDB
        retrieved_chunks = self.retriever.retrieve(
            query=clean_q,
            document_id=request.document_id,
            version_tag=request.version_tag,
            top_k=top_k,
            similarity_threshold=threshold
        )

        # 2. Evaluate retrieval quality
        confidence, confidence_level = self.calculate_confidence(retrieved_chunks)
        limitations = self.evaluate_limitations(retrieved_chunks)

        # If no chunks passed threshold, reject safely with zero hallucination
        if not retrieved_chunks:
            return RAGQueryResponse(
                question=clean_q,
                answer="Insufficient evidence in the selected HLD documents to answer this question.",
                citations=[],
                retrieved_chunks=[],
                confidence=0.0,
                confidence_level="INSUFFICIENT",
                limitations=limitations,
                document_id_filter=request.document_id,
                version_filter=request.version_tag
            )

        # 3. Construct Grounded Prompt Payload
        evidence_blocks: List[str] = []
        for i, chunk in enumerate(retrieved_chunks, start=1):
            block = (
                f"[Chunk {i} | Source: {chunk.filename} | Version: {chunk.version_tag} | "
                f"Page: {chunk.page_number} | Section: {chunk.heading}]\n"
                f"{chunk.content}"
            )
            evidence_blocks.append(block)

        formatted_context = "\n\n".join(evidence_blocks)
        user_prompt = (
            f"RETRIEVED HLD EVIDENCE:\n"
            f"{formatted_context}\n\n"
            f"USER QUESTION:\n"
            f"{clean_q}"
        )

        # 4. Generate Grounded LLM Response
        try:
            answer = await self.llm_client.generate(
                system_prompt=GROUNDED_SYSTEM_PROMPT,
                user_prompt=user_prompt
            )
        except Exception as e:
            logger.error(f"LLM Generation failure: {e}", exc_info=True)
            answer = f"Error generating answer from LLM provider: {str(e)}"
            limitations.append(f"LLM generation failed: {str(e)}")

        # 5. Build Structured Citations
        citations: List[Citation] = []
        for i, chunk in enumerate(retrieved_chunks, start=1):
            snippet = chunk.content[:240].strip() + ("..." if len(chunk.content) > 240 else "")
            citations.append(Citation(
                citation_index=i,
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                filename=chunk.filename,
                version_tag=chunk.version_tag,
                page_number=chunk.page_number,
                heading=chunk.heading,
                source_type=chunk.source_type,
                similarity_score=round(chunk.similarity_score, 4),
                snippet=snippet
            ))

        return RAGQueryResponse(
            question=clean_q,
            answer=answer,
            citations=citations,
            retrieved_chunks=retrieved_chunks,
            confidence=confidence,
            confidence_level=confidence_level,
            limitations=limitations,
            document_id_filter=request.document_id,
            version_filter=request.version_tag
        )


def get_rag_service() -> RAGService:
    """Factory returning RAGService instance."""
    return RAGService()
