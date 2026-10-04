import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Trash2, 
  Download, 
  CheckCircle, 
  Clock, 
  AlertOctagon, 
  Layers, 
  FileCheck,
  Search,
  Eye,
  X,
  Play,
  RotateCw,
  Loader2,
  BookOpen,
  Database
} from 'lucide-react';
import { 
  DocumentResponse, 
  deleteDocument, 
  processDocument, 
  getDocumentDownloadUrl,
  ingestDocument,
  fetchIngestionStatus,
  DocumentIngestionStatusResponse
} from '../services/api';
import PageViewerModal from './PageViewerModal';

interface DocumentListProps {
  documents: DocumentResponse[];
  loading: boolean;
  onRefresh: () => void;
  onOpenUpload: () => void;
}

export default function DocumentList({ documents, loading, onRefresh, onOpenUpload }: DocumentListProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDoc, setSelectedDoc] = useState<DocumentResponse | null>(null);
  const [viewingPagesDoc, setViewingPagesDoc] = useState<DocumentResponse | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [ingestingId, setIngestingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [ingestionInfo, setIngestionInfo] = useState<DocumentIngestionStatusResponse | null>(null);

  useEffect(() => {
    if (selectedDoc) {
      fetchIngestionStatus(selectedDoc.id)
        .then(info => setIngestionInfo(info))
        .catch(() => setIngestionInfo(null));
    } else {
      setIngestionInfo(null);
    }
  }, [selectedDoc]);

  const filteredDocs = documents.filter((doc) => {
    const term = searchTerm.toLowerCase();
    return (
      doc.filename.toLowerCase().includes(term) ||
      (doc.title && doc.title.toLowerCase().includes(term)) ||
      doc.version_tag.toLowerCase().includes(term)
    );
  });

  const handleProcess = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setProcessingId(id);
    try {
      await processDocument(id);
      onRefresh();
    } catch (err: any) {
      alert(`Document processing failed: ${err.message}`);
    } finally {
      setProcessingId(null);
    }
  };

  const handleIngest = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setIngestingId(id);
    try {
      const res = await ingestDocument(id);
      onRefresh();
      if (selectedDoc?.id === id) {
        setIngestionInfo({
          document_id: id,
          status: res.status,
          total_chunks: res.total_chunks,
          total_vectors: res.total_vectors,
          collection_name: res.collection_name,
          embedding_model: res.embedding_model,
          ingested_at: res.ingested_at
        });
      }
    } catch (err: any) {
      alert(`Knowledge ingestion failed: ${err.message}`);
    } finally {
      setIngestingId(null);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete "${name}"? This removes the uploaded file and associated records.`)) {
      return;
    }
    setDeletingId(id);
    try {
      await deleteDocument(id);
      if (selectedDoc?.id === id) {
        setSelectedDoc(null);
      }
      onRefresh();
    } catch (err: any) {
      alert(`Failed to delete document: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatDate = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoStr;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'uploaded':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-medium bg-cyan-950/80 text-cyan-300 border border-cyan-800/60">
            <CheckCircle className="w-3 h-3 text-cyan-400" />
            <span>UPLOADED</span>
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-medium bg-amber-950/80 text-amber-300 border border-amber-800/60">
            <Clock className="w-3 h-3 text-amber-400 animate-spin" />
            <span>PROCESSING</span>
          </span>
        );
      case 'processed':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
            <CheckCircle className="w-3 h-3 text-emerald-400" />
            <span>PROCESSED</span>
          </span>
        );
      case 'ingested':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-medium bg-purple-950/80 text-purple-300 border border-purple-800/60">
            <Database className="w-3 h-3 text-purple-400" />
            <span>INGESTED</span>
          </span>
        );
      case 'failed':
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-medium bg-rose-950/80 text-rose-300 border border-rose-800/60">
            <AlertOctagon className="w-3 h-3 text-rose-400" />
            <span>FAILED</span>
          </span>
        );
    }
  };

  return (
    <div className="space-y-4">
      {/* Top action bar: Search & Upload button */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by title, filename, or version..."
            className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
          <button
            onClick={onRefresh}
            className="px-3 py-2 text-xs font-medium rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 transition-colors"
          >
            Refresh
          </button>
          <button
            onClick={onOpenUpload}
            className="flex items-center space-x-1.5 px-4 py-2 text-xs font-medium rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-600/20 transition-all"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Upload HLD PDF</span>
          </button>
        </div>
      </div>

      {/* Document Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-mono uppercase text-[10px]">
              <tr>
                <th className="py-3 px-4">Document / Architecture HLD</th>
                <th className="py-3 px-3">Revision</th>
                <th className="py-3 px-3">Pages</th>
                <th className="py-3 px-3">File Size</th>
                <th className="py-3 px-3">Pipeline Status</th>
                <th className="py-3 px-3">Uploaded At</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading && documents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    Loading AUTOSAR HLD documents...
                  </td>
                </tr>
              ) : filteredDocs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center">
                    <FileText className="w-10 h-10 text-slate-600 mx-auto mb-2" />
                    <p className="text-sm font-medium text-slate-300">No AUTOSAR HLD Documents Found</p>
                    <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                      {searchTerm ? 'No documents match your filter criteria.' : 'Upload an AUTOSAR High-Level Design PDF to begin architecture intelligence extraction and analysis.'}
                    </p>
                    {!searchTerm && (
                      <button
                        onClick={onOpenUpload}
                        className="mt-4 px-4 py-2 text-xs font-medium rounded-lg bg-cyan-600/80 hover:bg-cyan-600 text-white transition-colors"
                      >
                        Upload First HLD
                      </button>
                    )}
                  </td>
                </tr>
              ) : (
                filteredDocs.map((doc) => (
                  <tr
                    key={doc.id}
                    className="hover:bg-slate-800/40 transition-colors group cursor-pointer"
                    onClick={() => setSelectedDoc(doc)}
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 shrink-0">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <div className="font-semibold text-slate-200 truncate group-hover:text-cyan-300 transition-colors">
                            {doc.title || doc.filename}
                          </div>
                          <div className="text-[11px] text-slate-400 font-mono truncate">
                            {doc.filename}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-cyan-300 border border-slate-700">
                        {doc.version_tag}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <span className="font-mono text-slate-300">
                        {doc.page_count > 0 ? `${doc.page_count} pages` : 'Pending'}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-400">
                      {formatFileSize(doc.file_size_bytes)}
                    </td>
                    <td className="py-3 px-3">
                      {getStatusBadge(doc.status)}
                    </td>
                    <td className="py-3 px-3 text-slate-400 font-mono text-[11px]">
                      {formatDate(doc.created_at)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end space-x-1.5" onClick={(e) => e.stopPropagation()}>
                        {/* Process / Reprocess Button */}
                        {doc.status === 'uploaded' ? (
                          <button
                            onClick={(e) => handleProcess(e, doc.id)}
                            disabled={processingId === doc.id}
                            title="Process Document (Extract text, headings, tables)"
                            className="flex items-center space-x-1 px-2.5 py-1 text-[11px] font-medium rounded bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-600/50 transition-colors"
                          >
                            {processingId === doc.id ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <Play className="w-3 h-3" />
                            )}
                            <span>Process</span>
                          </button>
                        ) : (doc.status === 'processed' || doc.status === 'ingested') ? (
                          <>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setViewingPagesDoc(doc);
                              }}
                              title="Inspect Extracted Pages"
                              className="flex items-center space-x-1 px-2.5 py-1 text-[11px] font-medium rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/60 hover:bg-emerald-900/60 transition-colors"
                            >
                              <BookOpen className="w-3 h-3" />
                              <span>Pages ({doc.page_count})</span>
                            </button>

                            {/* Ingest into Vector DB */}
                            <button
                              onClick={(e) => handleIngest(e, doc.id)}
                              disabled={ingestingId === doc.id}
                              title={doc.status === 'ingested' ? "Re-ingest Chunks into ChromaDB" : "Ingest into ChromaDB Vector Store"}
                              className={`flex items-center space-x-1 px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
                                doc.status === 'ingested'
                                  ? 'bg-purple-950/60 text-purple-300 border border-purple-800/60 hover:bg-purple-900/60'
                                  : 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 hover:bg-indigo-600/50'
                              }`}
                            >
                              {ingestingId === doc.id ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                              ) : (
                                <Database className="w-3 h-3" />
                              )}
                              <span>{doc.status === 'ingested' ? 'Re-ingest' : 'Ingest'}</span>
                            </button>

                            <button
                              onClick={(e) => handleProcess(e, doc.id)}
                              disabled={processingId === doc.id}
                              title="Reprocess Document"
                              className="p-1 text-slate-400 hover:text-cyan-300 hover:bg-slate-800 rounded transition-colors"
                            >
                              <RotateCw className={`w-3.5 h-3.5 ${processingId === doc.id ? 'animate-spin text-cyan-400' : ''}`} />
                            </button>
                          </>
                        ) : null}

                        <button
                          onClick={() => setSelectedDoc(doc)}
                          title="View Metadata"
                          className="p-1.5 text-slate-400 hover:text-cyan-300 hover:bg-slate-800 rounded transition-colors"
                        >
                          <Eye className="w-4 h-4" />
                        </button>

                        <a
                          href={getDocumentDownloadUrl(doc.id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          title="Preview Original PDF"
                          className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-800 rounded transition-colors"
                        >
                          <Download className="w-4 h-4" />
                        </a>

                        <button
                          onClick={() => handleDelete(doc.id, doc.filename)}
                          disabled={deletingId === doc.id}
                          title="Delete Document"
                          className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Document Details Drawer / Modal */}
      {selectedDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-2xl rounded-xl border border-slate-800 bg-slate-900 shadow-2xl p-6 relative">
            <button
              onClick={() => setSelectedDoc(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center space-x-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                <FileCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">{selectedDoc.title || selectedDoc.filename}</h3>
                <p className="text-xs text-slate-400 font-mono">AUTOSAR HLD Specification Metadata</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-slate-500 uppercase tracking-wider text-[10px] font-mono">Document ID</span>
                <p className="text-slate-300 font-mono truncate">{selectedDoc.id}</p>
              </div>

              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-slate-500 uppercase tracking-wider text-[10px] font-mono">Original Filename</span>
                <p className="text-slate-300 font-mono truncate">{selectedDoc.filename}</p>
              </div>

              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-slate-500 uppercase tracking-wider text-[10px] font-mono">Revision & Pages</span>
                <p className="text-slate-200 font-mono">
                  {selectedDoc.version_tag} • {selectedDoc.page_count} Pages
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-slate-500 uppercase tracking-wider text-[10px] font-mono">File Size</span>
                <p className="text-slate-200 font-mono">{formatFileSize(selectedDoc.file_size_bytes)}</p>
              </div>

              <div className="col-span-2 p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-slate-500 uppercase tracking-wider text-[10px] font-mono">SHA-256 Checksum</span>
                <p className="text-cyan-300 font-mono text-[11px] break-all">{selectedDoc.file_hash}</p>
              </div>

              <div className="col-span-2 p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-slate-500 uppercase tracking-wider text-[10px] font-mono">Pipeline Status</span>
                <div className="mt-1 flex items-center justify-between">
                  {getStatusBadge(selectedDoc.status)}
                  <span className="text-[11px] text-slate-400 font-mono">Uploaded: {formatDate(selectedDoc.created_at)}</span>
                </div>
                {selectedDoc.error_message && (
                  <p className="text-rose-400 text-xs mt-2 bg-rose-950/40 p-2 rounded border border-rose-900/50">
                    Error: {selectedDoc.error_message}
                  </p>
                )}
              </div>

              {/* Ingestion & Vector DB Section */}
              <div className="col-span-2 p-3 rounded-lg bg-purple-950/20 border border-purple-800/40 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-purple-300 font-semibold text-[11px] flex items-center space-x-1.5">
                    <Database className="w-3.5 h-3.5 text-purple-400" />
                    <span>Knowledge Vector Store (ChromaDB)</span>
                  </span>
                  {selectedDoc.status === 'ingested' ? (
                    <span className="text-[10px] font-mono bg-purple-900/60 text-purple-300 px-2 py-0.5 rounded border border-purple-700/60">
                      LIVE IN CHROMA
                    </span>
                  ) : (
                    <button
                      onClick={(e) => handleIngest(e, selectedDoc.id)}
                      disabled={ingestingId === selectedDoc.id}
                      className="px-2.5 py-1 text-[11px] font-medium rounded bg-indigo-600/40 text-indigo-200 border border-indigo-500/50 hover:bg-indigo-600/60 transition-colors flex items-center space-x-1"
                    >
                      {ingestingId === selectedDoc.id && <Loader2 className="w-3 h-3 animate-spin" />}
                      <span>Ingest into ChromaDB</span>
                    </button>
                  )}
                </div>

                {ingestionInfo && ingestionInfo.total_vectors > 0 && (
                  <div className="grid grid-cols-3 gap-2 pt-1 font-mono text-[11px]">
                    <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                      <span className="text-slate-500 text-[10px] block">CHUNKS</span>
                      <span className="text-cyan-300 font-semibold">{ingestionInfo.total_chunks}</span>
                    </div>
                    <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                      <span className="text-slate-500 text-[10px] block">VECTORS</span>
                      <span className="text-purple-300 font-semibold">{ingestionInfo.total_vectors}</span>
                    </div>
                    <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                      <span className="text-slate-500 text-[10px] block">COLLECTION</span>
                      <span className="text-slate-300 truncate block text-[10px]">{ingestionInfo.collection_name}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between space-x-3 mt-6 pt-4 border-t border-slate-800">
              {(selectedDoc.status === 'processed' || selectedDoc.status === 'ingested') ? (
                <button
                  onClick={() => {
                    const doc = selectedDoc;
                    setSelectedDoc(null);
                    setViewingPagesDoc(doc);
                  }}
                  className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-cyan-600/30 border border-cyan-500/40 text-cyan-300 hover:bg-cyan-600/50 text-xs font-medium transition-colors"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>Inspect Extracted Pages</span>
                </button>
              ) : (
                <span />
              )}

              <div className="flex items-center space-x-2">
                <a
                  href={getDocumentDownloadUrl(selectedDoc.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download PDF</span>
                </a>
                <button
                  onClick={() => setSelectedDoc(null)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Page Viewer Modal */}
      <PageViewerModal
        document={viewingPagesDoc}
        isOpen={Boolean(viewingPagesDoc)}
        onClose={() => setViewingPagesDoc(null)}
      />
    </div>
  );
}
