import React, { useState, useEffect } from 'react';
import { 
  X, 
  Layers, 
  ChevronLeft, 
  ChevronRight, 
  FileText, 
  Table as TableIcon, 
  Type, 
  Scan, 
  CheckCircle, 
  Hash, 
  AlertCircle,
  Loader2
} from 'lucide-react';
import { DocumentResponse, DocumentPageResponse, fetchDocumentPages } from '../services/api';

interface PageViewerModalProps {
  document: DocumentResponse | null;
  isOpen: boolean;
  onClose: () => void;
  initialPageNumber?: number;
}

export default function PageViewerModal({ document, isOpen, onClose, initialPageNumber }: PageViewerModalProps) {
  const [pages, setPages] = useState<DocumentPageResponse[]>([]);
  const [currentPageIndex, setCurrentPageIndex] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (document && isOpen) {
      setLoading(true);
      setError(null);
      fetchDocumentPages(document.id)
        .then((data) => {
          setPages(data);
          if (initialPageNumber) {
            const idx = data.findIndex(p => p.page_number === initialPageNumber);
            setCurrentPageIndex(idx >= 0 ? idx : 0);
          } else {
            setCurrentPageIndex(0);
          }
        })
        .catch((err) => {
          setError(err.message || 'Failed to fetch processed pages.');
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [document, isOpen, initialPageNumber]);

  if (!isOpen || !document) return null;

  const currentPage = pages[currentPageIndex];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-150">
      <div className="w-full max-w-5xl h-[88vh] rounded-xl border border-slate-800 bg-slate-900 shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between shrink-0 bg-slate-950/60">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-sm font-semibold text-white truncate max-w-md">
                  {document.title || document.filename}
                </h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-800">
                  {document.version_tag}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800">
                  PROCESSED
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                Preserved Page-by-Page Architectural Extraction • Total Pages: {pages.length || document.page_count}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        {loading ? (
          <div className="flex-1 flex flex-col items-center justify-center space-y-3">
            <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
            <p className="text-xs text-slate-400 font-mono">Loading extracted architectural pages...</p>
          </div>
        ) : error ? (
          <div className="flex-1 flex flex-col items-center justify-center p-6 text-center space-y-3">
            <AlertCircle className="w-10 h-10 text-rose-400" />
            <p className="text-sm font-medium text-rose-300">{error}</p>
            <p className="text-xs text-slate-500 max-w-md">
              Please ensure this document has been processed via the "Process Document" action.
            </p>
          </div>
        ) : pages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
            <FileText className="w-10 h-10 text-slate-600 mb-2" />
            <p className="text-sm text-slate-300">No processed page data found for this document.</p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            {/* Page Navigation Ribbon */}
            <div className="px-6 py-2.5 bg-slate-950/40 border-b border-slate-800/80 flex items-center justify-between shrink-0">
              <div className="flex items-center space-x-1.5">
                <span className="text-xs text-slate-400 font-mono mr-2">Pages:</span>
                {pages.map((p, idx) => (
                  <button
                    key={p.id}
                    onClick={() => setCurrentPageIndex(idx)}
                    className={`px-3 py-1 rounded text-xs font-mono font-medium transition-all ${
                      currentPageIndex === idx
                        ? 'bg-cyan-600 text-white shadow-sm shadow-cyan-600/30'
                        : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-700'
                    }`}
                  >
                    Pg {p.page_number}
                  </button>
                ))}
              </div>

              <div className="flex items-center space-x-2">
                <button
                  disabled={currentPageIndex === 0}
                  onClick={() => setCurrentPageIndex((prev) => Math.max(0, prev - 1))}
                  className="p-1 rounded bg-slate-800 text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-xs font-mono text-slate-300">
                  {currentPageIndex + 1} / {pages.length}
                </span>
                <button
                  disabled={currentPageIndex === pages.length - 1}
                  onClick={() => setCurrentPageIndex((prev) => Math.min(pages.length - 1, prev + 1))}
                  className="p-1 rounded bg-slate-800 text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Current Page Content Layout */}
            {currentPage && (
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {/* Page Metadata Bar */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                    <span className="text-[10px] text-slate-500 font-mono uppercase tracking-wider block">
                      Preserved Page
                    </span>
                    <span className="text-base font-semibold text-white font-mono">
                      Page {currentPage.page_number}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                    <span className="text-[10px] text-slate-500 font-mono uppercase tracking-wider block">
                      Extraction Mode
                    </span>
                    <span className="text-xs font-semibold text-emerald-400 font-mono flex items-center mt-1">
                      {currentPage.is_ocr ? (
                        <>
                          <Scan className="w-3.5 h-3.5 mr-1 text-amber-400" />
                          <span>OCR Fallback</span>
                        </>
                      ) : (
                        <>
                          <CheckCircle className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                          <span>Native PyMuPDF</span>
                        </>
                      )}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                    <span className="text-[10px] text-slate-500 font-mono uppercase tracking-wider block">
                      Text Metrics
                    </span>
                    <span className="text-xs font-semibold text-slate-200 font-mono mt-1 block">
                      {currentPage.word_count} words • {currentPage.char_count} chars
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                    <span className="text-[10px] text-slate-500 font-mono uppercase tracking-wider block">
                      Detected Tables
                    </span>
                    <span className="text-xs font-semibold text-cyan-300 font-mono mt-1 block">
                      {currentPage.tables.length} table{currentPage.tables.length !== 1 ? 's' : ''} parsed
                    </span>
                  </div>
                </div>

                {/* Detected Headings */}
                {currentPage.headings.length > 0 && (
                  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-2">
                    <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300">
                      <Type className="w-4 h-4 text-cyan-400" />
                      <span>Detected Architecture Headings & Sections</span>
                    </div>
                    <div className="flex flex-wrap gap-2 pt-1">
                      {currentPage.headings.map((h, i) => (
                        <span
                          key={i}
                          className="px-2.5 py-1 rounded-md text-xs font-medium bg-slate-800/90 text-cyan-300 border border-slate-700"
                        >
                          {h}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Extracted Tables View */}
                {currentPage.tables.length > 0 && (
                  <div className="space-y-4">
                    <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300">
                      <TableIcon className="w-4 h-4 text-indigo-400" />
                      <span>Extracted Architectural Tables ({currentPage.tables.length})</span>
                    </div>
                    {currentPage.tables.map((tbl, tblIdx) => (
                      <div key={tblIdx} className="rounded-lg border border-slate-800 overflow-hidden bg-slate-950">
                        <div className="overflow-x-auto">
                          <table className="w-full text-left text-xs">
                            <thead className="bg-slate-900 border-b border-slate-800 text-cyan-300 font-mono text-[11px]">
                              <tr>
                                {tbl.rows[0]?.map((col, cIdx) => (
                                  <th key={cIdx} className="py-2.5 px-3 font-semibold">
                                    {col || `Col ${cIdx + 1}`}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800/60 font-mono text-[11px] text-slate-300">
                              {tbl.rows.slice(1).map((row, rIdx) => (
                                <tr key={rIdx} className="hover:bg-slate-900/40">
                                  {row.map((cell, cIdx) => (
                                    <td key={cIdx} className="py-2 px-3">
                                      {cell || '—'}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Full Extracted Page Text */}
                <div className="space-y-2">
                  <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300">
                    <FileText className="w-4 h-4 text-emerald-400" />
                    <span>Extracted Page Text (Citation Target Context)</span>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
                    {currentPage.cleaned_text || <span className="text-slate-600 italic">No text content detected on this page.</span>}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
