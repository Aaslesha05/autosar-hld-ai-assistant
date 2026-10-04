# AUTOSAR HLD AI Assistant — System Architecture

This document describes the end-to-end architecture, data flows, and subsystem interactions of the AUTOSAR High-Level Design (HLD) AI Assistant.

---

## 1. High-Level Architecture Diagram

```
+---------------------------------------------------------------------------------+
|                                React Frontend                                   |
|   (Document Repository, Processing Actions, RAG Chat, Citation Cards, Inspector)|
+---------------------------------------------------------------------------------+
                                        │
                                        │ REST API Calls (HTTP / JSON / Multipart)
                                        ▼
+---------------------------------------------------------------------------------+
|                               FastAPI Backend                                   |
|   (/api/documents, /api/documents/{id}/process, /api/query, /health)            |
+---------------------------------------------------------------------------------+
                                        │
                                        │ Raw PDF Stream
                                        ▼
+---------------------------------------------------------------------------------+
|                              Document Processing                                |
|   (PyMuPDF Native Text & Tables + Tesseract OCR Engine Fallback for Scanned)    |
+---------------------------------------------------------------------------------+
                                        │
                                        │ Page-by-Page JSON & SQLite Records
                                        ▼
+---------------------------------------------------------------------------------+
|                            SQLite / Processed Pages                             |
|   (data/autosar_hld.db: documents, document_pages, document_ingestions)         |
+---------------------------------------------------------------------------------+
                                        │
                                        │ Structured Page Streams
                                        ▼
+---------------------------------------------------------------------------------+
|                           Context-Aware Chunking Engine                         |
|   (Hierarchical Section & Heading Preservation + Table-to-Markdown Formatting)  |
+---------------------------------------------------------------------------------+
                                        │
                                        │ Contextual Text Chunks
                                        ▼
+---------------------------------------------------------------------------------+
|                       Sentence Transformer Embeddings                           |
|   (all-MiniLM-L6-v2: Normalized 384-dimensional dense vectors)                  |
+---------------------------------------------------------------------------------+
                                        │
                                        │ Vector Upsert / Query
                                        ▼
+---------------------------------------------------------------------------------+
|                             Persistent ChromaDB                                 |
|   (data/chroma: autosar_hld_chunks collection, HNSW Cosine Index)               |
+---------------------------------------------------------------------------------+
                                        │
                                        │ Semantic Similarity Top-K Chunks
                                        ▼
+---------------------------------------------------------------------------------+
|                                  Retriever                                      |
|   (Cosine Distance Scoring, Document ID & Version Filtering, Threshold Pruning) |
+---------------------------------------------------------------------------------+
                                        │
                                        │ Filtered Relevant Chunks
                                        ▼
+---------------------------------------------------------------------------------+
|                             Grounded RAG Service                                |
|   (Context Assembly + Strict Hallucination Refusal Prompting)                   |
+---------------------------------------------------------------------------------+
                                        │
                                        │ Grounded Prompt Payload
                                        ▼
+---------------------------------------------------------------------------------+
|                                Configured LLM                                   |
|   (Mock Deterministic Client / OpenAI / Anthropic / Gemini / Ollama)            |
+---------------------------------------------------------------------------------+
                                        │
                                        │ Synthesized Grounded Response
                                        ▼
+---------------------------------------------------------------------------------+
|                               Answer + Citations                                |
|   (Response JSON: Answer + Page Citations + Retrieval Confidence + Limitations) |
+---------------------------------------------------------------------------------+
                                        │
                                        │ Citation Click Interaction
                                        ▼
+---------------------------------------------------------------------------------+
|                                 PDF Page Viewer                                 |
|   (PageViewerModal: Jumps directly to exact document page number)               |
+---------------------------------------------------------------------------------+
```

---

## 2. Pipeline Subsystems

### A. Document Ingestion Subsystem
- **Validation**: Enforces strict `%PDF` magic header checks, 50 MB size limits, and cryptographic SHA-256 calculation.
- **Persistence**: SQLite database with Write-Ahead Logging (WAL) and foreign keys enabled.

### B. Extraction & OCR Fallback Subsystem
- **Native Extraction**: Uses PyMuPDF (`fitz`) to extract page-by-page text, table bounding boxes, and heading hierarchies.
- **Automated OCR Fallback**: Pages with $< 50$ characters of native text trigger rendering to 300 DPI images followed by Tesseract OCR analysis, tagging `is_ocr = true` in page metadata.

### C. Chunking & Embedding Subsystem
- **Chunking**: Uses hierarchical splitting (`500` character limit, `80` overlap) that respects section headings (`1. System Architectural Overview`, `2. Software Components`) and reformats tables into structured Markdown.
- **Embeddings**: Loads `all-MiniLM-L6-v2` as a process-level singleton, generating 384-dimensional dense vectors in batches.

### D. Persistent Vector Store
- **ChromaDB**: Stored under `data/chroma` using the `autosar_hld_chunks` collection.
- **Index**: HNSW with cosine distance metric.
- **Document Isolation**: Supports metadata filtering by `document_id` and `version_tag`.
- **Idempotency**: Deletes old vectors for a document before inserting updated ones.

### E. Grounded RAG & Multi-Provider LLM
- **Strict Grounding**: `GROUNDED_SYSTEM_PROMPT` prohibits external speculation or invention of timing or ASIL categories.
- **Controlled Refusal**: If evidence is missing, returns:
  `"Insufficient evidence in the selected HLD documents to answer this question."`
- **Providers**: Multi-provider client abstraction supporting local mock for deterministic CI/CD, OpenAI, Anthropic, Gemini, and Ollama.

### F. Traceable Citation Chain
```
User Question
    │
    ▼
Generated Answer Statement
    │
    ▼
Citation [#1] (Doc: AUTOSAR_BodyControl_HLD_v1.0.pdf, Page 3, Section: Run_ReadDoorSensors)
    │
    ▼
Retrieved Chunk (..._p3_c1, Cosine Score: 0.5419)
    │
    ▼
Page Inspector Modal (Navigated to Page 3)
```
