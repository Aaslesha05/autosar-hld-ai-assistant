import React, { useState, useRef } from 'react';
import { UploadCloud, File, AlertCircle, X, Check, Loader2 } from 'lucide-react';
import { uploadDocument, DocumentResponse } from '../services/api';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (newDoc: DocumentResponse) => void;
}

export default function DocumentUploadModal({ isOpen, onClose, onUploadSuccess }: DocumentUploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [versionTag, setVersionTag] = useState('v1.0');
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileSelect = (selectedFile: File) => {
    setError(null);
    if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setError('Invalid file format. Only AUTOSAR HLD documents in PDF format (.pdf) are supported.');
      return;
    }
    if (selectedFile.size > 50 * 1024 * 1024) {
      setError('File size exceeds the 50 MB maximum limit.');
      return;
    }
    setFile(selectedFile);
    if (!title) {
      // Auto-populate title from clean filename
      const baseName = selectedFile.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
      setTitle(baseName);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select an AUTOSAR HLD PDF document.');
      return;
    }

    setUploading(true);
    setError(null);
    try {
      const response = await uploadDocument(file, title.trim() || undefined, versionTag.trim() || 'v1.0');
      onUploadSuccess(response.document);
      handleClose();
    } catch (err: any) {
      setError(err.message || 'Failed to upload document.');
    } finally {
      setUploading(false);
    }
  };

  const handleClose = () => {
    setFile(null);
    setTitle('');
    setVersionTag('v1.0');
    setError(null);
    setUploading(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-lg rounded-xl border border-slate-800 bg-slate-900 shadow-2xl p-6 relative">
        {/* Close Button */}
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center space-x-3 mb-5">
          <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <UploadCloud className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">Upload AUTOSAR HLD PDF</h2>
            <p className="text-xs text-slate-400">High-Level Design Specification Document Ingestion</p>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-start space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
            <span className="leading-relaxed">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Drop Zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer transition-all ${
              isDragging
                ? 'border-cyan-400 bg-cyan-950/20'
                : file
                ? 'border-emerald-500/50 bg-emerald-950/10'
                : 'border-slate-800 hover:border-slate-700 bg-slate-950/50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileSelect(e.target.files[0]);
                }
              }}
            />

            {file ? (
              <div className="flex items-center space-x-3 text-left w-full px-2">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
                  <File className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate">{file.name}</p>
                  <p className="text-xs text-slate-400 font-mono">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB • PDF Ready
                  </p>
                </div>
                <span className="text-xs px-2 py-1 bg-emerald-950 border border-emerald-800 text-emerald-300 rounded font-mono">
                  READY
                </span>
              </div>
            ) : (
              <>
                <UploadCloud className="w-10 h-10 text-cyan-400 mb-2 opacity-80" />
                <p className="text-sm font-medium text-slate-300">
                  Drop your AUTOSAR HLD PDF here, or <span className="text-cyan-400 underline">browse</span>
                </p>
                <p className="text-[11px] text-slate-500 mt-1 font-mono">
                  Accepts .pdf (Max size: 50 MB)
                </p>
              </>
            )}
          </div>

          {/* Document Title */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Document Title <span className="text-slate-500">(Optional)</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Body Control Module Architecture v1.0"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 transition-colors"
            />
          </div>

          {/* Revision Version Tag */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Architecture Revision Tag
            </label>
            <div className="grid grid-cols-4 gap-2">
              {['v1.0', 'v1.1', 'v2.0', 'custom'].map((tag) => (
                <button
                  type="button"
                  key={tag}
                  onClick={() => {
                    if (tag === 'custom') {
                      setVersionTag('v');
                    } else {
                      setVersionTag(tag);
                    }
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                    versionTag === tag || (tag === 'custom' && !['v1.0', 'v1.1', 'v2.0'].includes(versionTag))
                      ? 'bg-cyan-950/80 border border-cyan-500 text-cyan-300'
                      : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {tag}
                </button>
              ))}
            </div>
            {!['v1.0', 'v1.1', 'v2.0'].includes(versionTag) && (
              <input
                type="text"
                value={versionTag}
                onChange={(e) => setVersionTag(e.target.value)}
                placeholder="Custom version (e.g. v2.1-draft)"
                className="mt-2 w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500"
              />
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={handleClose}
              disabled={uploading}
              className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!file || uploading}
              className="flex items-center space-x-2 px-5 py-2 text-xs font-medium rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed text-white shadow-lg shadow-cyan-600/20 transition-all"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Validating & Storing...</span>
                </>
              ) : (
                <>
                  <UploadCloud className="w-3.5 h-3.5" />
                  <span>Upload HLD PDF</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
