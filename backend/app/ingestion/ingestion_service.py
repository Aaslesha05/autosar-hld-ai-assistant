"""
ingestion_service.py
--------------------
Orchestrates the full knowledge-base ingestion pipeline:
Processed Document -> Load Pages -> Context-Aware Chunks -> SentenceTransformer Embeddings -> ChromaDB.

Separate from the future RAG query service.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.database import get_connection
from app.ingestion.pdf_processor import PDFProcessor
from app.ingestion.chunker import AUTOSARChunker
from app.ingestion.embedding_service import get_embedding_service
from app.ingestion.vector_store import get_vector_store
from app.schemas.chunk import DocumentIngestionResponse, DocumentIngestionStatusResponse

logger = logging.getLogger("autosar_hld_ingestion_service")

class DocumentIngestionService:
    @classmethod
    def ingest_document(cls, document_id: str) -> DocumentIngestionResponse:
        """
        Executes the complete document ingestion pipeline into ChromaDB.
        1. Validates document existence.
        2. Ensures document has been processed (triggers PDFProcessor if needed).
        3. Loads structured pages.
        4. Generates context-aware chunks with architectural metadata.
        5. Computes dense vector embeddings in batches.
        6. Idempotently writes/updates vectors in ChromaDB.
        7. Records ingestion metadata in SQLite.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?;", (document_id,))
        doc_row = cursor.fetchone()

        if not doc_row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{document_id}' not found."
            )

        doc_dict = dict(doc_row)

        # 1. If document is only 'uploaded' or previously 'failed', process it first
        if doc_dict["status"] in ["uploaded", "failed"]:
            logger.info(f"Document {document_id} status is '{doc_dict['status']}' — auto-processing first.")
            conn.close()
            PDFProcessor.process_document(document_id)
            conn = get_connection()
            cursor = conn.cursor()

        # 2. Fetch processed pages
        pages = PDFProcessor.get_document_pages(document_id)
        if not pages:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document '{document_id}' has no processed pages available for chunking."
            )

        # 3. Create Chunks
        chunker = AUTOSARChunker()
        chunks = chunker.create_chunks_from_document(
            document_id=document_id,
            pages=pages,
            doc_meta=doc_dict
        )

        if not chunks:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No valid text chunks could be extracted from document '{document_id}'."
            )

        # 4. Generate Embeddings
        embedding_service = get_embedding_service()
        chunk_texts = [c.content for c in chunks]
        embeddings = embedding_service.embed_texts(chunk_texts)

        # 5. Store in ChromaDB
        vector_store = get_vector_store()
        vectors_stored = vector_store.upsert_chunks(chunks, embeddings)

        # 6. Record Ingestion in SQLite
        ingested_at_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO document_ingestions (
                document_id, collection_name, chunk_count, vector_count,
                embedding_model, status, ingested_at
            ) VALUES (?, ?, ?, ?, ?, 'ingested', ?);
        """, (
            document_id,
            vector_store.collection_name,
            len(chunks),
            vectors_stored,
            embedding_service.model_name,
            ingested_at_iso
        ))

        # Update document status to 'ingested'
        cursor.execute("""
            UPDATE documents 
            SET status = 'ingested', updated_at = ?
            WHERE id = ?;
        """, (ingested_at_iso, document_id))

        conn.commit()
        conn.close()

        logger.info(
            f"Successfully ingested document {document_id}: {len(chunks)} chunks, {vectors_stored} vectors."
        )

        return DocumentIngestionResponse(
            message=f"Document successfully ingested into ChromaDB. {len(chunks)} chunks and {vectors_stored} vectors stored.",
            document_id=document_id,
            status="ingested",
            total_chunks=len(chunks),
            total_vectors=vectors_stored,
            collection_name=vector_store.collection_name,
            embedding_model=embedding_service.model_name,
            ingested_at=ingested_at_iso
        )

    @classmethod
    def get_ingestion_status(cls, document_id: str) -> DocumentIngestionStatusResponse:
        """Query ingestion status and ChromaDB vector count for a document."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?;", (document_id,))
        doc_row = cursor.fetchone()

        if not doc_row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{document_id}' not found."
            )

        cursor.execute("SELECT * FROM document_ingestions WHERE document_id = ?;", (document_id,))
        ingestion_row = cursor.fetchone()
        conn.close()

        vector_store = get_vector_store()
        live_vector_count = vector_store.count_document_vectors(document_id)

        if ingestion_row:
            return DocumentIngestionStatusResponse(
                document_id=document_id,
                status=ingestion_row["status"],
                total_chunks=ingestion_row["chunk_count"],
                total_vectors=live_vector_count,
                collection_name=ingestion_row["collection_name"],
                embedding_model=ingestion_row["embedding_model"],
                ingested_at=ingestion_row["ingested_at"]
            )

        return DocumentIngestionStatusResponse(
            document_id=document_id,
            status="not_ingested" if live_vector_count == 0 else "ingested",
            total_chunks=live_vector_count,
            total_vectors=live_vector_count,
            collection_name=vector_store.collection_name,
            embedding_model=settings.EMBEDDING_MODEL,
            ingested_at=None
        )
