import React, { useState } from 'react';
import { 
  MessageSquare, 
  Send, 
  FileText, 
  Layers, 
  AlertCircle, 
  CheckCircle2, 
  HelpCircle, 
  ChevronRight, 
  ChevronDown, 
  Sparkles, 
  ExternalLink, 
  Sliders, 
  BookOpen, 
  ShieldAlert, 
  Info,
  Clock,
  Cpu
} from 'lucide-react';
import { 
  DocumentResponse, 
  RAGQueryRequest, 
  RAGQueryResponse, 
  Citation, 
  RetrievedChunk, 
  queryRAG 
} from '../services/api';
import PageViewerModal from './PageViewerModal';

interface RAGChatProps {
  documents: DocumentResponse[];
}

export default function RAGChat({ documents }: RAGChatProps) {
  const [question, setQuestion] = useState<string>('');
  const [selectedDocId, setSelectedDocId] = useState<string>('all');
  const [selectedVersion, setSelectedVersion] = useState<string>('all');
  const [topK, setTopK] = useState<number>(4);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<RAGQueryResponse | null>(null);
  
  // Modal viewer state for citation interaction
  const [viewerDoc, setViewerDoc] = useState<DocumentResponse | null>(null);
  const [viewerPage, setViewerPage] = useState<number>(1);
  const [isViewerOpen, setIsViewerOpen] = useState<boolean>(false);

  // Expanded chunk toggle
  const [showRawChunks, setShowRawChunks] = useState<boolean>(false);

  const samplePrompts = [
    {
      title: "Cycle Time",
      query: "What is the cycle time of Run_ReadDoorSensors?"
    },
    {
      title: "Components in DoorStatus_If",
      query: "Which software components are involved in DoorStatus_If?"
    },
    {
      title: "v1.0 vs v2.0 Architecture",
      query: "What changed between the available v1.0 and v2.0 information regarding the body control architecture?"
    },
    {
      title: "Unsupported (Negative Test)",
      query: "What is the exact ECU hardware part number?"
    }
  ];

  const handleQuery = async (queryText?: string) => {
    const textToSend = queryText || question;
    if (!textToSend.trim()) return;

    setLoading(true);
    setError(null);

    const payload: RAGQueryRequest = {
      question: textToSend.trim(),
      document_id: selectedDocId !== 'all' ? selectedDocId : null,
      version_tag: selectedVersion !== 'all' ? selectedVersion : null,
      top_k: topK,
      similarity_threshold: 0.30
    };

    try {
      const res = await queryRAG(payload);
      setResponse(res);
    } catch (err: any) {
      setError(err.message || 'RAG Query failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenCitation = (citation: Citation) => {
    const doc = documents.find(d => d.id === citation.document_id);
    if (doc) {
      setViewerDoc(doc);
      setViewerPage(citation.page_number);
      setIsViewerOpen(true);
    } else {
      // Find by filename if ID was transient
      const docByFilename = documents.find(d => d.filename === citation.filename);
      if (docByFilename) {
        setViewerDoc(docByFilename);
        setViewerPage(citation.page_number);
        setIsViewerOpen(true);
      }
    }
  };

  const isInsufficient = response && (
    response.confidence_level === 'INSUFFICIENT' || 
    Boolean(response.answer && response.answer.includes('Insufficient evidence in the selected HLD documents'))
  );

  const getConfidenceBadge = (level: string, score: number) => {
    switch (level) {
      case 'HIGH':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800">
            HIGH CONFIDENCE ({((score ?? 0) * 100).toFixed(1)}%)
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-blue-950/80 text-blue-400 border border-blue-800">
            MEDIUM CONFIDENCE ({((score ?? 0) * 100).toFixed(1)}%)
          </span>
        );
      case 'LOW':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-amber-950/80 text-amber-400 border border-amber-800">
            LOW CONFIDENCE ({((score ?? 0) * 100).toFixed(1)}%)
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-rose-950/80 text-rose-400 border border-rose-800">
            INSUFFICIENT EVIDENCE
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="rounded-xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900/90 to-slate-950 p-5 shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start space-x-3.5">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-wide flex items-center gap-2">
                AUTOSAR HLD Grounded Engineering Assistant
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950 border border-cyan-800 text-cyan-400">
                  RAG Pipeline Active
                </span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Strict context grounding. Questions are answered solely from verified ChromaDB HLD chunks with traceable page citations.
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2 text-xs text-slate-400 font-mono bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-800">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span>ChromaDB: autosar_hld_chunks</span>
          </div>
        </div>
      </div>

      {/* Query Control Panel */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
        {/* Filters Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pb-3 border-b border-slate-800/80 text-xs">
          <div>
            <label className="block text-slate-400 mb-1 font-medium">Document Scope</label>
            <select
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Ingested Documents</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename} ({doc.version_tag})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-slate-400 mb-1 font-medium">Version Tag Filter</label>
            <select
              value={selectedVersion}
              onChange={(e) => setSelectedVersion(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Revisions</option>
              <option value="v1.0">v1.0 (Baseline)</option>
              <option value="v2.0">v2.0 (Updated)</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 mb-1 font-medium">Evidence Top-K Chunks: {topK}</label>
            <input
              type="range"
              min="2"
              max="8"
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full accent-cyan-500 cursor-pointer mt-1"
            />
          </div>
        </div>

        {/* Input Bar */}
        <div className="relative">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleQuery();
              }
            }}
            placeholder="Ask an AUTOSAR High-Level Design question (e.g., runnable period, interface mapping, ASIL classification)..."
            rows={3}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 resize-none font-sans"
          />

          <div className="absolute right-3 bottom-3 flex items-center space-x-2">
            <button
              onClick={() => handleQuery()}
              disabled={loading || !question.trim()}
              className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-medium rounded-lg shadow flex items-center space-x-1.5 transition-all"
            >
              {loading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Retrieving...</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Ask Assistant</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Quick Sample Inquiries */}
        <div className="space-y-1.5">
          <span className="text-[11px] text-slate-400 font-mono">Suggested HLD Inquiries:</span>
          <div className="flex flex-wrap gap-2">
            {samplePrompts.map((p, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setQuestion(p.query);
                  handleQuery(p.query);
                }}
                className="text-xs px-2.5 py-1 rounded-md bg-slate-950 border border-slate-800 text-slate-300 hover:border-cyan-500/50 hover:text-cyan-300 transition-colors flex items-center space-x-1"
              >
                <span>{p.title}</span>
                <ChevronRight className="w-3 h-3 text-slate-500" />
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error Callout */}
      {error && (
        <div className="p-4 rounded-xl border border-rose-900/50 bg-rose-950/20 text-rose-300 flex items-start space-x-3 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
          <div>
            <div className="font-semibold text-rose-200">Query Error</div>
            <div className="mt-0.5 text-rose-300/90">{error}</div>
          </div>
        </div>
      )}

      {/* Initial Empty / Guidance State */}
      {!response && !loading && !error && (
        <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-8 text-center max-w-2xl mx-auto space-y-4">
          <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 mx-auto">
            <BookOpen className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-white">AUTOSAR Grounded Verification Engine Ready</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Select an ingested HLD document above, choose a suggested query or type a question to perform context-grounded retrieval.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left pt-2">
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/50 text-[11px] space-y-1">
              <span className="font-mono text-cyan-400 font-semibold">1. Scope</span>
              <p className="text-slate-400">Target a specific HLD or search across all ingested revisions.</p>
            </div>
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/50 text-[11px] space-y-1">
              <span className="font-mono text-blue-400 font-semibold">2. Retrieve</span>
              <p className="text-slate-400">ChromaDB semantic search prunes irrelevant chunks below similarity threshold.</p>
            </div>
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/50 text-[11px] space-y-1">
              <span className="font-mono text-emerald-400 font-semibold">3. Verify</span>
              <p className="text-slate-400">Every statement includes interactive citations linked to original page viewer.</p>
            </div>
          </div>
        </div>
      )}

      {/* RAG Results Display */}
      {response && (
        <div className="space-y-5 animate-in fade-in duration-200">
          {/* Main Answer Card */}
          <div className={`rounded-xl border p-6 transition-all ${
            isInsufficient 
              ? 'border-amber-700/60 bg-amber-950/15' 
              : 'border-slate-800 bg-slate-900/70 shadow-xl'
          }`}>
            {/* Answer Card Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-2.5">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                  isInsufficient 
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30' 
                    : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                }`}>
                  {isInsufficient ? <ShieldAlert className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">
                    {isInsufficient ? 'Insufficient Evidence Rejection' : 'Grounded HLD Response'}
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Engineered from {response.retrieved_chunks?.length ?? 0} ChromaDB context chunks{response.query_metadata?.llm_provider ? ` (${response.query_metadata.llm_provider})` : ''}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                {getConfidenceBadge(response.confidence_level, response.confidence)}
              </div>
            </div>

            {/* Answer Content */}
            <div className="pt-4 text-sm leading-relaxed text-slate-200 whitespace-pre-wrap font-sans">
              {response.answer}
            </div>

            {/* Limitations Notice */}
            {response.limitations && response.limitations.length > 0 && (
              <div className="mt-5 p-3 rounded-lg border border-amber-900/40 bg-amber-950/20 text-xs text-amber-300/90 space-y-1">
                <div className="font-semibold text-amber-200 flex items-center space-x-1.5">
                  <Info className="w-3.5 h-3.5" />
                  <span>Retrieval Limitations & Advisories</span>
                </div>
                <ul className="list-disc list-inside space-y-0.5 pl-1 text-[11px]">
                  {response.limitations.map((lim, idx) => (
                    <li key={idx}>{lim}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Citations Grid */}
          {response.citations && response.citations.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Traceable Source Citations ({response.citations.length})</span>
                </h4>
                <span className="text-[11px] text-slate-500">
                  Click citation to inspect original extracted page
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {response.citations.map((c, idx) => (
                  <div
                    key={c.citation_index ?? idx}
                    onClick={() => handleOpenCitation(c)}
                    className="group rounded-xl border border-slate-800 bg-slate-900/50 p-4 hover:border-cyan-500/50 hover:bg-slate-900 transition-all cursor-pointer shadow-sm relative overflow-hidden"
                  >
                    <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rounded-full blur-xl group-hover:bg-cyan-500/10 pointer-events-none transition-all" />

                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center space-x-2">
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950 text-cyan-400 border border-cyan-800">
                          #{c.citation_index}
                        </span>
                        <span className="text-xs font-semibold text-slate-200 group-hover:text-cyan-300 transition-colors truncate max-w-[200px]">
                          {c.filename}
                        </span>
                      </div>

                      <div className="flex items-center space-x-1.5">
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-blue-950 text-blue-300 border border-blue-900">
                          {c.version_tag}
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300">
                          Page {c.page_number}
                        </span>
                      </div>
                    </div>

                    <div className="mt-2 text-xs font-medium text-slate-400 flex items-center space-x-1 truncate">
                      <span className="text-slate-500">Section:</span>
                      <span className="text-slate-300">{c.heading || 'HLD Content'}</span>
                    </div>

                    <div className="mt-2 text-[11px] text-slate-400/90 italic bg-slate-950/60 p-2.5 rounded border border-slate-800/80 line-clamp-3">
                      "{c.snippet}"
                    </div>

                    <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex items-center justify-between text-[11px]">
                      <span className="text-slate-500 font-mono">
                        Match: {((c.similarity_score ?? 0) * 100).toFixed(1)}% {c.is_ocr && '• [OCR]'}
                      </span>
                      <span className="text-cyan-400 group-hover:text-cyan-300 flex items-center space-x-1 font-medium">
                        <span>Inspect Page {c.page_number}</span>
                        <ExternalLink className="w-3 h-3" />
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Raw Retrieved Chunks Inspector */}
          <div className="border border-slate-800 rounded-xl bg-slate-900/30 overflow-hidden">
            <button
              onClick={() => setShowRawChunks(!showRawChunks)}
              className="w-full px-4 py-2.5 text-xs text-slate-400 hover:text-slate-200 flex items-center justify-between transition-colors"
            >
              <div className="flex items-center space-x-2">
                <Sliders className="w-3.5 h-3.5 text-slate-400" />
                <span>Diagnostic Context Chunks ({response.retrieved_chunks?.length ?? 0} vectors)</span>
              </div>
              {showRawChunks ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>

            {showRawChunks && (
              <div className="p-4 border-t border-slate-800 space-y-3 bg-slate-950/50">
                {(response.retrieved_chunks || []).map((chk, idx) => (
                  <div key={chk.chunk_id || idx} className="p-3 rounded-lg border border-slate-800 bg-slate-900/80 text-xs space-y-1.5">
                    <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                      <span>Chunk {idx + 1}: {chk.chunk_id ? `${chk.chunk_id.substring(0, 16)}...` : 'Vector'}</span>
                      <span>Cosine Distance: {chk.distance !== undefined ? chk.distance.toFixed(4) : 'N/A'} | Score: {chk.similarity_score !== undefined ? `${(chk.similarity_score * 100).toFixed(1)}%` : 'N/A'}</span>
                    </div>
                    <pre className="text-[11px] font-mono text-slate-300 whitespace-pre-wrap bg-slate-950 p-2.5 rounded border border-slate-800 max-h-40 overflow-y-auto">
                      {chk.content || chk.text || ''}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Page Viewer Modal when Citation Clicked */}
      <PageViewerModal
        document={viewerDoc}
        isOpen={isViewerOpen}
        onClose={() => setIsViewerOpen(false)}
        initialPageNumber={viewerPage}
      />
    </div>
  );
}
