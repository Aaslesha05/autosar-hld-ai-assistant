"""
retriever.py
------------
Dedicated retrieval component for querying ChromaDB knowledge base.
Supports document filtering, version filtering, top_k selection, and similarity thresholding.
"""

import logging
from typing import List, Optional, Dict, Any

from app.core.config import settings
from app.ingestion.vector_store import get_vector_store
from app.ingestion.embedding_service import get_embedding_service
from app.schemas.rag import RetrievedChunk

logger = logging.getLogger("autosar_hld_retriever")

class HLDRetriever:
    def __init__(self):
        self.vector_store = get_vector_store()
        self.embedding_service = get_embedding_service()

    def retrieve(
        self,
        query: str,
        document_id: Optional[str] = None,
        version_tag: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.35
    ) -> List[RetrievedChunk]:
        """
        Execute similarity search against ChromaDB vectors with optional scoping:
        - document_id: restrict to single document
        - version_tag: restrict to specific architectural version (e.g. 'v1.0', 'v2.0')
        - similarity_threshold: prune weak hits below threshold
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        # 1. Generate Query Vector
        query_vec = self.embedding_service.embed_query(clean_query)

        # 2. Build ChromaDB Where Filter
        where_conditions: List[Dict[str, Any]] = []
        if document_id:
            where_conditions.append({"document_id": document_id})
        if version_tag:
            where_conditions.append({"version_tag": version_tag})

        where_filter: Optional[Dict[str, Any]] = None
        if len(where_conditions) == 1:
            where_filter = where_conditions[0]
        elif len(where_conditions) > 1:
            where_filter = {"$and": where_conditions}

        # 3. Query ChromaDB Collection
        # Query slightly more (top_k * 2) so we can filter by threshold cleanly
        fetch_k = min(top_k * 2, 40)
        try:
            results = self.vector_store.collection.query(
                query_embeddings=[query_vec],
                n_results=fetch_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            logger.error(f"ChromaDB retrieval error: {e}", exc_info=True)
            return []

        chunks: List[RetrievedChunk] = []
        if results and results.get("ids") and len(results["ids"]) > 0:
            ids = results["ids"][0]
            docs = results["documents"][0] if results.get("documents") else []
            metas = results["metadatas"][0] if results.get("metadatas") else []
            dists = results["distances"][0] if results.get("distances") else []

            for idx, c_id in enumerate(ids):
                dist = float(dists[idx]) if idx < len(dists) else 1.0
                similarity = max(0.0, min(1.0, 1.0 - dist))

                # Filter by similarity threshold
                if similarity < similarity_threshold:
                    continue

                meta = metas[idx] if idx < len(metas) else {}
                content = docs[idx] if idx < len(docs) else ""

                chunk = RetrievedChunk(
                    chunk_id=c_id,
                    document_id=str(meta.get("document_id", "")),
                    filename=str(meta.get("filename", "")),
                    version_tag=str(meta.get("version_tag", "")),
                    page_number=int(meta.get("page_number", 1)),
                    heading=str(meta.get("heading", "General")),
                    source_type=str(meta.get("source_type", "text")),
                    is_ocr=bool(meta.get("is_ocr", False)),
                    distance=dist,
                    similarity_score=similarity,
                    content=content
                )
                chunks.append(chunk)

        # Sort descending by similarity
        chunks.sort(key=lambda c: c.similarity_score, reverse=True)
        return chunks[:top_k]


_retriever_instance: Optional[HLDRetriever] = None

def get_retriever() -> HLDRetriever:
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = HLDRetriever()
    return _retriever_instance

