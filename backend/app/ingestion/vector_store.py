"""
vector_store.py
---------------
Persistent ChromaDB vector store integration for AUTOSAR HLD architecture chunks.

Guarantees:
- Persistent local storage under data/chroma
- Isolation of embeddings by document_id
- Idempotent ingestion (safe deletion of prior document vectors before upsert)
- Custom SentenceTransformers embedding support (embedding_function=None)
- Semantic similarity search verification with source metadata preservation
"""

import os
import logging
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.schemas.chunk import Chunk

logger = logging.getLogger("autosar_hld_vector_store")

class ChromaVectorStore:
    _instance: Optional["ChromaVectorStore"] = None

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        self.persist_directory = persist_directory or settings.CHROMA_PATH
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=None,
            metadata={"hnsw:space": "cosine"}
        )

    def delete_document_vectors(self, document_id: str) -> int:
        """
        Delete all existing vectors associated with a document_id to guarantee idempotency.
        Returns the number of deleted vectors.
        """
        try:
            existing = self.collection.get(where={"document_id": document_id})
            count = len(existing.get("ids", []))
            if count > 0:
                self.collection.delete(where={"document_id": document_id})
                logger.info(f"Deleted {count} existing vectors for document {document_id}")
            return count
        except Exception as e:
            logger.warning(f"Error checking/deleting existing vectors for {document_id}: {e}")
            return 0

    def upsert_chunks(self, chunks: List[Chunk], embeddings: List[List[float]]) -> int:
        """
        Idempotently store chunks and their corresponding embeddings into ChromaDB.
        1. Remove prior vectors for the target document.
        2. Insert new vectors with full metadata.
        """
        if not chunks:
            return 0

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks provided but received {len(embeddings)} embeddings."
            )

        document_id = chunks[0].metadata.document_id

        # 1. Clear any prior vectors for idempotent re-ingestion
        self.delete_document_vectors(document_id)

        # 2. Prepare payload
        ids = [c.chunk_id for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [c.metadata.to_chroma_metadata() for c in chunks]

        # 3. Store in ChromaDB
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        logger.info(f"Successfully upserted {len(chunks)} vectors into collection '{self.collection_name}' for doc '{document_id}'.")
        return len(chunks)

    def get_document_chunks(self, document_id: str) -> Dict[str, Any]:
        """Retrieve all vector entries and metadata stored for a document."""
        return self.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"]
        )

    def count_document_vectors(self, document_id: str) -> int:
        """Count total vectors currently stored for a document."""
        res = self.collection.get(
            where={"document_id": document_id},
            include=[]
        )
        return len(res.get("ids", []))

    def similarity_search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform cosine similarity search against stored embeddings.
        Optionally restrict scope to a single document_id for strict isolation.
        """
        where_filter = {"document_id": document_id} if document_id else None
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        hits: List[Dict[str, Any]] = []
        if results and results.get("ids") and len(results["ids"]) > 0:
            ids = results["ids"][0]
            docs = results["documents"][0] if results.get("documents") else []
            metas = results["metadatas"][0] if results.get("metadatas") else []
            dists = results["distances"][0] if results.get("distances") else []

            for idx, c_id in enumerate(ids):
                hits.append({
                    "chunk_id": c_id,
                    "content": docs[idx] if idx < len(docs) else "",
                    "metadata": metas[idx] if idx < len(metas) else {},
                    "distance": dists[idx] if idx < len(dists) else 1.0,
                    "similarity_score": 1.0 - (dists[idx] if idx < len(dists) else 1.0)
                })

        return hits


def get_vector_store() -> ChromaVectorStore:
    """Singleton getter for the persistent ChromaVectorStore."""
    if ChromaVectorStore._instance is None:
        ChromaVectorStore._instance = ChromaVectorStore()
    return ChromaVectorStore._instance
