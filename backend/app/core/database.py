import os
import sqlite3
from typing import Optional
from app.core.config import settings

def get_db_path() -> str:
    """Extract SQLite database file path from DATABASE_URL or fallback."""
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        path = db_url.replace("sqlite:///", "")
    else:
        path = os.path.join(settings.BASE_DIR, "..", "data", "autosar_hld.db")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    return os.path.abspath(path)

def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with row factory enabled."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys and WAL mode for high concurrency
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db():
    """Initialize database tables for documents, processed pages, and workflow tracking."""
    conn = get_connection()
    cursor = conn.cursor()

    # Documents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        stored_filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size_bytes INTEGER NOT NULL,
        file_hash TEXT NOT NULL,
        page_count INTEGER DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'uploaded',
        error_message TEXT DEFAULT NULL,
        title TEXT DEFAULT NULL,
        version_tag TEXT DEFAULT 'v1.0',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # Indices for documents
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);")

    # Document Pages table (Phase 2 - PDF Processing)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_pages (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        page_number INTEGER NOT NULL,
        raw_text TEXT NOT NULL,
        cleaned_text TEXT NOT NULL,
        headings_json TEXT DEFAULT '[]',
        tables_json TEXT DEFAULT '[]',
        has_tables INTEGER DEFAULT 0,
        is_ocr INTEGER DEFAULT 0,
        word_count INTEGER DEFAULT 0,
        char_count INTEGER DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'success',
        created_at TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
        UNIQUE(document_id, page_number)
    );
    """)

    # Indices for document pages
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_pages_doc_id ON document_pages(document_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_pages_doc_page ON document_pages(document_id, page_number);")

    # Document Ingestions table (Phase 3 - Chunking & Vector DB Ingestion)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_ingestions (
        document_id TEXT PRIMARY KEY,
        collection_name TEXT NOT NULL,
        chunk_count INTEGER NOT NULL DEFAULT 0,
        vector_count INTEGER NOT NULL DEFAULT 0,
        embedding_model TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ingested',
        ingested_at TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_ingestions_doc_id ON document_ingestions(document_id);")

    conn.commit()
    conn.close()

# Auto-initialize tables upon module import
init_db()
