import React, { useEffect, useState } from 'react';
import { 
  Cpu, 
  FileText, 
  MessageSquare, 
  Network, 
  AlertTriangle, 
  GitCompare, 
  FileCheck2, 
  Settings as SettingsIcon, 
  CheckCircle2, 
  XCircle, 
  RefreshCw, 
  Server, 
  ShieldCheck, 
  Layers, 
  Database,
  Terminal,
  Activity,
  UploadCloud,
  FileCheck,
  HardDrive,
  BookOpen
} from 'lucide-react';
import { checkBackendHealth, fetchDocuments, HealthResponse, DocumentResponse } from './services/api';
import DocumentUploadModal from './components/DocumentUploadModal';
import DocumentList from './components/DocumentList';
import RAGChat from './components/RAGChat';

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'documents' | 'chat' | 'architecture' | 'issues' | 'compare' | 'reports' | 'settings'>('dashboard');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [docsLoading, setDocsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string>('');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await checkBackendHealth();
      setHealth(data);
      setLastChecked(new Date().toLocaleTimeString());
    } catch (err: any) {
      setError(err.message || 'Failed to reach FastAPI backend');
      setLastChecked(new Date().toLocaleTimeString());
    } finally {
      setLoading(false);
    }
  };

  const loadDocuments = async () => {
    setDocsLoading(true);
    try {
      const data = await fetchDocuments();
      setDocuments(data.documents);
    } catch (err: any) {
      console.error('Error fetching documents:', err);
    } finally {
      setDocsLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    loadDocuments();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const totalPages = documents.reduce((acc, doc) => acc + (doc.page_count || 0), 0);
  const totalBytes = documents.reduce((acc, doc) => acc + (doc.file_size_bytes || 0), 0);
  const processedDocsCount = documents.filter(d => d.status === 'processed').length;

  const formatTotalSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 bg-slate-900/60 flex flex-col justify-between shrink-0">
        <div>
          {/* Logo & Brand Header */}
          <div className="p-4 border-b border-slate-800 flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-semibold text-sm tracking-wide text-white">AUTOSAR HLD</h1>
              <p className="text-[10px] text-cyan-400 font-mono tracking-wider">AI ASSISTANT</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'dashboard'
                  ? 'bg-automotive-600/30 text-cyan-300 border border-cyan-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Activity className="w-4 h-4 text-cyan-400" />
              <span>Dashboard</span>
            </button>

            <button
              onClick={() => setActiveTab('documents')}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'documents'
                  ? 'bg-automotive-600/30 text-cyan-300 border border-cyan-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <FileText className="w-4 h-4 text-blue-400" />
              <div className="flex-1 flex items-center justify-between">
                <span>HLD Documents</span>
                {documents.length > 0 && (
                  <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-blue-950 border border-blue-800 text-blue-300">
                    {documents.length}
                  </span>
                )}
              </div>
            </button>

            <button
              onClick={() => setActiveTab('chat')}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'chat'
                  ? 'bg-automotive-600/30 text-cyan-300 border border-cyan-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <MessageSquare className="w-4 h-4 text-indigo-400" />
              <span>HLD Chat & RAG</span>
            </button>

            <button
              onClick={() => setActiveTab('architecture')}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'architecture'
                  ? 'bg-automotive-600/30 text-cyan-300 border border-cyan-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Network className="w-4 h-4 text-emerald-400" />
              <span>Architecture Graph</span>
            </button>

            <button
              onClick={() => setActiveTab('issues')}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'issues'
                  ? 'bg-automotive-600/30 text-cyan-300 border border-cyan-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>Inconsistency Check</span>
            </button>

            <button
              onClick={() => setActiveTab('compare')}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'compare'
                  ? 'bg-automotive-600/30 text-cyan-300 border border-cyan-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <GitCompare className="w-4 h-4 text-violet-400" />
              <span>Version Comparison</span>
            </button>

            <button
              onClick={() => setActiveTab('reports')}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'reports'
                  ? 'bg-automotive-600/30 text-cyan-300 border border-cyan-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <FileCheck2 className="w-4 h-4 text-teal-400" />
              <span>Structured Reports</span>
            </button>

            <button
              onClick={() => setActiveTab('settings')}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'settings'
                  ? 'bg-automotive-600/30 text-cyan-300 border border-cyan-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <SettingsIcon className="w-4 h-4 text-slate-400" />
              <span>System Settings</span>
            </button>
          </nav>
        </div>

        {/* Backend Status Footer Badge */}
        <div className="p-3 border-t border-slate-800 bg-slate-900/80">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400 flex items-center space-x-2">
              <Server className="w-3.5 h-3.5 text-slate-400" />
              <span>FastAPI Backend</span>
            </span>
            {loading ? (
              <span className="flex items-center text-amber-400 text-[11px] font-mono">
                <RefreshCw className="w-3 h-3 animate-spin mr-1" />
                checking...
              </span>
            ) : health?.status === 'healthy' ? (
              <span className="flex items-center text-emerald-400 text-[11px] font-mono">
                <CheckCircle2 className="w-3 h-3 mr-1" />
                ONLINE
              </span>
            ) : (
              <span className="flex items-center text-rose-400 text-[11px] font-mono">
                <XCircle className="w-3 h-3 mr-1" />
                OFFLINE
              </span>
            )}
          </div>
          <div className="mt-2 text-[10px] text-slate-500 flex justify-between">
            <span>v0.1.0 • Phase 2</span>
            <span>{lastChecked}</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-y-auto">
        {/* Top Header */}
        <header className="h-14 border-b border-slate-800 bg-slate-900/40 backdrop-blur px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3">
            <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-cyan-950/80 text-cyan-300 border border-cyan-800/50">
              AUTOSAR Classic & Adaptive 4.4+
            </span>
            <span className="text-slate-400 text-xs">|</span>
            <span className="text-xs text-slate-300 font-medium">Case Study 1: Document Analysis & Architecture RAG Assistant</span>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => { fetchHealth(); loadDocuments(); }}
              title="Refresh health and document lists"
              className="flex items-center space-x-1.5 px-2.5 py-1 text-xs rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-slate-300 transition-colors"
            >
              <RefreshCw className={`w-3 h-3 ${loading || docsLoading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
            <button
              onClick={() => setIsUploadModalOpen(true)}
              className="flex items-center space-x-1.5 px-3 py-1 text-xs rounded bg-cyan-600 hover:bg-cyan-500 text-white font-medium shadow-md shadow-cyan-600/20 transition-all"
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span>Upload HLD</span>
            </button>
            <div className="flex items-center space-x-1.5 px-2 py-1 rounded bg-slate-800/60 border border-slate-700/60 text-xs text-slate-300">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-[11px] font-mono">HUMAN-IN-THE-LOOP ACTIVE</span>
            </div>
          </div>
        </header>

        {/* Tab Body */}
        <div className="p-6 max-w-7xl mx-auto w-full space-y-6">
          {activeTab === 'dashboard' && (
            <>
              {/* Dashboard Hero Card */}
              <div className="rounded-xl border border-cyan-500/20 bg-gradient-to-r from-slate-900 via-slate-900 to-automotive-950 p-6 shadow-xl relative overflow-hidden">
                <div className="absolute top-0 right-0 transform translate-x-4 -translate-y-4 w-40 h-40 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        PHASE 2 COMPLETED
                      </span>
                      <span className="text-xs text-slate-400">• PDF Processing & Page Extraction</span>
                    </div>
                    <h2 className="text-xl font-bold text-white mt-2">
                      AUTOSAR HLD Architecture Intelligence Platform
                    </h2>
                    <p className="text-sm text-slate-300 mt-1 max-w-2xl">
                      Automating the extraction, semantic organization, port/signal mapping, and consistency verification for automotive High-Level Design specifications under ISO 26262 and AUTOSAR methodology.
                    </p>
                  </div>

                  {/* Status Pill */}
                  <div className="shrink-0 flex flex-col items-end">
                    {health?.status === 'healthy' ? (
                      <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs font-mono font-medium">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        <span>FASTAPI BACKEND ONLINE</span>
                      </div>
                    ) : (
                      <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs font-mono font-medium">
                        <span className="w-2 h-2 rounded-full bg-rose-400" />
                        <span>DISCONNECTED: {error || 'Connecting...'}</span>
                      </div>
                    )}
                    <span className="text-[11px] text-slate-400 mt-1">PyMuPDF Processing Engine</span>
                  </div>
                </div>

                {/* Dashboard KPI Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
                  <div className="p-4 rounded-lg bg-slate-900/80 border border-slate-800">
                    <div className="flex items-center justify-between text-slate-400 text-xs">
                      <span>Total HLD Documents</span>
                      <FileText className="w-4 h-4 text-cyan-400" />
                    </div>
                    <p className="text-2xl font-bold text-white mt-1">
                      {documents.length}
                    </p>
                    <p className="text-[11px] text-cyan-300 font-mono mt-0.5">
                      Ingested & Validated
                    </p>
                  </div>

                  <div className="p-4 rounded-lg bg-slate-900/80 border border-slate-800">
                    <div className="flex items-center justify-between text-slate-400 text-xs">
                      <span>Architecture Pages</span>
                      <Layers className="w-4 h-4 text-indigo-400" />
                    </div>
                    <p className="text-2xl font-bold text-white mt-1">
                      {totalPages}
                    </p>
                    <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                      Preserved 1-Indexed Pages
                    </p>
                  </div>

                  <div className="p-4 rounded-lg bg-slate-900/80 border border-slate-800">
                    <div className="flex items-center justify-between text-slate-400 text-xs">
                      <span>Processed Documents</span>
                      <BookOpen className="w-4 h-4 text-emerald-400" />
                    </div>
                    <p className="text-2xl font-bold text-white mt-1">
                      {processedDocsCount} / {documents.length}
                    </p>
                    <p className="text-[11px] text-emerald-400 font-mono mt-0.5">
                      Text & Tables Extracted
                    </p>
                  </div>

                  <div className="p-4 rounded-lg bg-slate-900/80 border border-slate-800">
                    <div className="flex items-center justify-between text-slate-400 text-xs">
                      <span>Storage Footprint</span>
                      <HardDrive className="w-4 h-4 text-amber-400" />
                    </div>
                    <p className="text-2xl font-bold text-white mt-1">
                      {formatTotalSize(totalBytes)}
                    </p>
                    <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                      PDFs & Structured JSON
                    </p>
                  </div>
                </div>
              </div>

              {/* Document Inventory Section on Dashboard */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
                    <FileText className="w-4 h-4 text-cyan-400" />
                    <span>Uploaded & Processed AUTOSAR HLD Specifications</span>
                  </h3>
                  <button
                    onClick={() => setActiveTab('documents')}
                    className="text-xs text-cyan-400 hover:text-cyan-300 font-medium"
                  >
                    View Full Repository →
                  </button>
                </div>
                <DocumentList
                  documents={documents}
                  loading={docsLoading}
                  onRefresh={loadDocuments}
                  onOpenUpload={() => setIsUploadModalOpen(true)}
                />
              </div>
            </>
          )}

          {activeTab === 'documents' && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-bold text-white">AUTOSAR HLD Document Repository</h2>
                <p className="text-xs text-slate-400">
                  Manage High-Level Design PDFs, execute the PDF processing pipeline, inspect extracted page-by-page text, headings, and tables, and review preserved page numbers.
                </p>
              </div>
              <DocumentList
                documents={documents}
                loading={docsLoading}
                onRefresh={loadDocuments}
                onOpenUpload={() => setIsUploadModalOpen(true)}
              />
            </div>
          )}

          {activeTab === 'chat' && (
            <RAGChat documents={documents} />
          )}

          {/* Placeholders for upcoming phases */}
          {['architecture', 'issues', 'compare', 'reports', 'settings'].includes(activeTab) && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center max-w-xl mx-auto space-y-4">
              <div className="w-12 h-12 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-cyan-400 mx-auto">
                <Terminal className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-white capitalize">
                  {activeTab === 'architecture' && 'Phase 9: Interactive Architecture Relationship Graph'}
                  {activeTab === 'issues' && 'Phase 10: Potential Inconsistency & Safety Rule Engine'}
                  {activeTab === 'compare' && 'Phase 11: Multi-Version Architectural Diff'}
                  {activeTab === 'reports' && 'Phase 12: Structured Report Generator'}
                  {activeTab === 'settings' && 'System Configuration & Provider Settings'}
                </h3>
                <p className="text-xs text-slate-400 mt-2">
                  This phase will be implemented incrementally per the master delivery roadmap.
                </p>
              </div>
              <button
                onClick={() => setActiveTab('documents')}
                className="px-4 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              >
                Back to Document Repository
              </button>
            </div>
          )}
        </div>
      </main>

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={(newDoc) => {
          setDocuments((prev) => [newDoc, ...prev]);
        }}
      />
    </div>
  );
}
