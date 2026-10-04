# AUTOSAR HLD AI Assistant

An intelligent, context-grounded AI assistant engineered for automotive software architects and functional safety engineers working with AUTOSAR Classic and Adaptive High-Level Design (HLD) specifications.

The system ingests multi-page AUTOSAR architecture documents, extracts structured text and interface tables with OCR fallback, indexes semantic representations into a persistent vector database, and generates strictly grounded architectural responses with traceable page-level citations.

---

## Key Capabilities

1. **Document Validation & Ingestion**
   - Cryptographic SHA-256 deduplication and PDF structural verification via PyMuPDF.
   - Upload metadata tracking: software revisions (`v1.0`, `v2.0`), page counts, byte sizes.
2. **Page-Level PDF Extraction & OCR Fallback**
   - Page-by-page text, heading hierarchy, and table extraction.
   - Automated detection of scanned/sparse pages with Tesseract OCR fallback.
3. **Context-Aware Chunking & Vector Store**
   - Heading and section boundaries preserved with table-to-Markdown formatting.
   - 384-dimensional dense vectors generated via `all-MiniLM-L6-v2` SentenceTransformers.
   - Persistent ChromaDB indexing (`data/chroma`) with document and version isolation.
4. **Grounded RAG Question Answering**
   - Strict grounding prompt: refuses unsupported questions without hallucination.
   - Traceable citation chain: `Answer → Citation → Retrieved Chunk → Page Number → PDF Document`.
   - Multi-provider LLM support: `mock`, `openai`, `anthropic`, `gemini`, `ollama`.
5. **Interactive Automotive Dashboard**
   - High-density dark-mode interface built with React 18, TypeScript, and Tailwind CSS.
   - Live citation cards with direct "Inspect Page" button opening the extracted document page.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, TypeScript 5, Vite 6, Tailwind CSS, Lucide Icons |
| **Backend API** | FastAPI, Python 3.13, Pydantic v2, Uvicorn |
| **PDF Extraction & OCR** | PyMuPDF (fitz), Tesseract OCR (v5.4.0), PIL |
| **Embeddings & Vector DB**| Sentence Transformers (`all-MiniLM-L6-v2`), ChromaDB (Persistent) |
| **Storage & Metadata** | SQLite (WAL mode), JSON structured output cache |
| **LLM Orchestration** | Pluggable multi-provider architecture (Mock, OpenAI, Anthropic, Gemini, Ollama) |

---

## Quick Start

### 1. Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows: venv\Scripts\activate, Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit dashboard at: `http://localhost:5173`

For detailed configuration and prerequisites, see [SETUP.md](file:///c:/Users/aasle/Downloads/autosar-hld-ai-assistant/docs/SETUP.md).

---

## Documentation Index

- [System Architecture](file:///c:/Users/aasle/Downloads/autosar-hld-ai-assistant/docs/ARCHITECTURE.md)
- [Setup & Deployment Guide](file:///c:/Users/aasle/Downloads/autosar-hld-ai-assistant/docs/SETUP.md)
- [Evaluation Benchmark](file:///c:/Users/aasle/Downloads/autosar-hld-ai-assistant/docs/EVALUATION.md)
- [Known Limitations](file:///c:/Users/aasle/Downloads/autosar-hld-ai-assistant/docs/LIMITATIONS.md)
- [Project Progress & Audit Log](file:///c:/Users/aasle/Downloads/autosar-hld-ai-assistant/docs/PROJECT_PROGRESS.md)
