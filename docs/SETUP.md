# AUTOSAR HLD AI Assistant — Setup & Deployment Guide

This guide details the exact steps required to install, configure, test, and run the AUTOSAR HLD AI Assistant locally on Windows, Linux, or macOS.

---

## 1. System Requirements

- **Python**: 3.10 to 3.13 (Python 3.13 verified)
- **Node.js**: 18.x or higher (Node 20+ recommended)
- **Tesseract OCR**: 5.x (Required for scanned PDF image OCR fallback)
- **RAM**: Minimum 8 GB (16 GB recommended for local embedding model)

---

## 2. Environment Configuration

### Backend Configuration
Create `backend/.env` from the provided template:
```bash
cp backend/.env.example backend/.env
```

Key environment variables:
```ini
ENVIRONMENT=development
HOST=127.0.0.1
PORT=8000
DEBUG=True

# LLM Provider Configuration: 'mock', 'openai', 'anthropic', 'gemini', 'ollama'
LLM_PROVIDER=mock
LLM_API_KEY=
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.0

# Embedding Model
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Storage Limits
MAX_UPLOAD_SIZE_MB=50
CHROMA_COLLECTION_NAME=autosar_hld_chunks
```

---

## 3. Installation Steps

### Step A: Backend Setup
```bash
# 1. Navigate to backend directory
cd backend

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Verify database initialization
python -c "from app.core.database import init_db; init_db(); print('Database initialized.')"
```

### Step B: Frontend Setup
```bash
# 1. Navigate to frontend directory
cd ../frontend

# 2. Install dependencies
npm install

# 3. Run production build test
npm run build
```

---

## 4. Running the Application

### Start the FastAPI Backend
```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Base URL: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`
- Health Endpoint: `http://127.0.0.1:8000/health`

### Start the React Frontend Dev Server
```bash
cd frontend
npm run dev
```
- Web Application: `http://localhost:5173`
- The Vite proxy will automatically forward `/api` and `/health` requests to `127.0.0.1:8000`.

---

## 5. Running Automated Tests

### Run Full Backend Test Suite
```bash
cd backend
venv\Scripts\activate
pytest tests/ -v
```

### Run Clean End-to-End Ingestion & RAG Benchmark
```bash
# From repository root
backend\venv\Scripts\python.exe scripts/e2e_demo_verify.py
```
This script initializes clean storage, processes and ingests both `v1.0` and `v2.0` sample HLD documents, and runs the 10-question evaluation benchmark.
