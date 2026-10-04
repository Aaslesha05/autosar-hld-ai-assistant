export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
  llm_provider: string;
  embedding_provider: string;
  details: {
    storage: {
      chroma_dir_exists: boolean;
      upload_dir_exists: boolean;
      processed_dir_exists: boolean;
    };
    config: {
      max_upload_size_mb: number;
      allowed_extensions: string[];
    };
  };
}

export interface DocumentResponse {
  id: string;
  filename: string;
  stored_filename: string;
  file_size_bytes: number;
  file_hash: string;
  page_count: number;
  status: 'uploaded' | 'processing' | 'processed' | 'ingested' | 'failed';
  error_message?: string | null;
  title?: string | null;
  version_tag: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total: number;
}

export interface DocumentUploadResponse {
  message: string;
  document: DocumentResponse;
}

export interface TableData {
  table_index: number;
  rows: (string | null)[][];
  row_count: number;
  col_count: number;
}

export interface DocumentPageResponse {
  id: string;
  document_id: string;
  page_number: number;
  raw_text: string;
  cleaned_text: string;
  headings: string[];
  tables: TableData[];
  has_tables: boolean;
  is_ocr: boolean;
  word_count: number;
  char_count: number;
  status: string;
  created_at: string;
}

export interface DocumentProcessingResponse {
  message: string;
  document_id: string;
  status: string;
  total_pages_processed: number;
  ocr_pages_count: number;
  tables_found_count: number;
  total_words: number;
  pages: DocumentPageResponse[];
}

export async function checkBackendHealth(): Promise<HealthResponse> {
  const response = await fetch('/health');
  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
  }
  return response.json();
}

export async function fetchDocuments(): Promise<DocumentListResponse> {
  const response = await fetch('/api/documents');
  if (!response.ok) {
    throw new Error(`Failed to fetch documents: ${response.statusText}`);
  }
  return response.json();
}

export async function uploadDocument(
  file: File, 
  title?: string, 
  versionTag: string = 'v1.0'
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (title) formData.append('title', title);
  if (versionTag) formData.append('version_tag', versionTag);

  const response = await fetch('/api/documents/upload', {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `Upload failed with status: ${response.status}`);
  }

  return data;
}

export async function deleteDocument(documentId: string): Promise<void> {
  const response = await fetch(`/api/documents/${documentId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `Failed to delete document: ${response.status}`);
  }
}

export function getDocumentDownloadUrl(documentId: string): string {
  return `/api/documents/${documentId}/file`;
}

export async function processDocument(documentId: string): Promise<DocumentProcessingResponse> {
  const response = await fetch(`/api/documents/${documentId}/process`, {
    method: 'POST',
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `Processing failed with status: ${response.status}`);
  }
  return data;
}

export async function fetchDocumentPages(documentId: string): Promise<DocumentPageResponse[]> {
  const response = await fetch(`/api/documents/${documentId}/pages`);
  if (!response.ok) {
    throw new Error(`Failed to fetch document pages: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchDocumentPage(documentId: string, pageNumber: number): Promise<DocumentPageResponse> {
  const response = await fetch(`/api/documents/${documentId}/pages/${pageNumber}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch page ${pageNumber}: ${response.statusText}`);
  }
  return response.json();
}

// --- Phase 3: Ingestion API ---

export interface DocumentIngestionResponse {
  message: string;
  document_id: string;
  status: string;
  total_chunks: number;
  total_vectors: number;
  collection_name: string;
  embedding_model: string;
  ingested_at: string;
}

export interface DocumentIngestionStatusResponse {
  document_id: string;
  status: string;
  total_chunks: number;
  total_vectors: number;
  collection_name: string;
  embedding_model: string;
  ingested_at?: string | null;
}

export async function ingestDocument(documentId: string): Promise<DocumentIngestionResponse> {
  const response = await fetch(`/api/documents/${documentId}/ingest`, {
    method: 'POST',
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `Ingestion failed with status: ${response.status}`);
  }
  return data;
}

export async function fetchIngestionStatus(documentId: string): Promise<DocumentIngestionStatusResponse> {
  const response = await fetch(`/api/documents/${documentId}/ingestion`);
  if (!response.ok) {
    throw new Error(`Failed to fetch ingestion status: ${response.statusText}`);
  }
  return response.json();
}

// --- Phase 4: RAG Query API ---

export interface Citation {
  citation_index: number;
  chunk_id: string;
  document_id: string;
  filename: string;
  version_tag: string;
  page_number: number;
  heading: string;
  source_type: string;
  similarity_score: number;
  snippet: string;
  is_ocr?: boolean;
}

export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  filename: string;
  version_tag: string;
  page_number: number;
  heading: string;
  source_type: string;
  is_ocr: boolean;
  distance: number;
  similarity_score: number;
  content: string;
  text?: string;
  chunk_index?: number;
}

export interface RAGQueryRequest {
  question: string;
  document_id?: string | null;
  version_tag?: string | null;
  top_k?: number;
  similarity_threshold?: number;
}

export interface RAGQueryResponse {
  question: string;
  answer: string;
  citations: Citation[];
  retrieved_chunks: RetrievedChunk[];
  confidence: number;
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT';
  limitations: string[];
  document_id_filter?: string | null;
  version_filter?: string | null;
  query_metadata?: {
    question?: string;
    document_id?: string | null;
    version_tag?: string | null;
    top_k?: number;
    similarity_threshold?: number;
    llm_provider?: string;
    total_retrieved?: number;
  };
}

export async function queryRAG(request: RAGQueryRequest): Promise<RAGQueryResponse> {
  const response = await fetch('/api/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `Query failed with status: ${response.status}`);
  }
  return data;
}

