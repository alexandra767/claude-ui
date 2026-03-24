import { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Upload, Clipboard, Copy, Check, Trash2, Download,
  FileText, Image, Link, Type, Send, X, Smartphone, Monitor, Cpu, RefreshCw
} from 'lucide-react';

interface SharedItem {
  id: string;
  type: 'text' | 'image' | 'file' | 'link';
  content: string;
  filename: string | null;
  file_size: number;
  mime_type: string;
  source_device: string;
  has_file: boolean;
  created_at: string;
}

const API = '/api/share';
const getToken = () => localStorage.getItem('token') || '';
const headers = () => {
  const h: Record<string, string> = {};
  const token = getToken();
  if (token) h['Authorization'] = `Bearer ${token}`;
  return h;
};
const fileUrl = (itemId: string) => `${API}/file/${itemId}?token=${encodeURIComponent(getToken())}`;

function detectDevice(): string {
  const ua = navigator.userAgent;
  if (/iPhone|iPad/.test(ua)) return 'iPhone';
  if (/Macintosh/.test(ua)) return 'MacBook';
  if (/Android/.test(ua)) return 'Android';
  return 'Desktop';
}

export default function Share() {
  const navigate = useNavigate();
  const [items, setItems] = useState<SharedItem[]>([]);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const device = detectDevice();

  const loadItems = useCallback(async () => {
    try {
      const res = await fetch(`${API}/items`, { headers: headers() });
      if (res.ok) setItems(await res.json());
    } catch {}
  }, []);

  useEffect(() => {
    loadItems();
    // Only poll when the Share page is visible
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible' && window.location.pathname === '/share') {
        loadItems();
      }
    }, 15000); // Poll every 15s
    return () => clearInterval(interval);
  }, [loadItems]);

  const shareText = async () => {
    if (!text.trim()) return;
    setSending(true);
    try {
      await fetch(`${API}/text`, {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: text.trim(), source_device: device }),
      });
      setText('');
      loadItems();
    } catch {}
    setSending(false);
  };

  const shareFile = async (file: File) => {
    setSending(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_device', device);
    try {
      await fetch(`${API}/file`, {
        method: 'POST',
        headers: headers(),
        body: formData,
      });
      loadItems();
    } catch {}
    setSending(false);
  };

  const handlePaste = async (e: React.ClipboardEvent) => {
    const clipItems = e.clipboardData.items;
    for (const item of Array.from(clipItems)) {
      if (item.type.startsWith('image/')) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) await shareFile(file);
        return;
      }
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    for (const file of Array.from(e.dataTransfer.files)) {
      await shareFile(file);
    }
  };

  const copyContent = (item: SharedItem) => {
    navigator.clipboard.writeText(item.content);
    setCopiedId(item.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const deleteItem = async (id: string) => {
    await fetch(`${API}/items/${id}`, { method: 'DELETE', headers: headers() });
    setItems((prev) => prev.filter((i) => i.id !== id));
  };

  const clearAll = async () => {
    await fetch(`${API}/items`, { method: 'DELETE', headers: headers() });
    setItems([]);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  };

  const timeAgo = (iso: string) => {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  const DeviceIcon = ({ name }: { name: string }) => {
    if (name === 'iPhone') return <Smartphone className="w-3 h-3" />;
    if (name === 'MacBook') return <Monitor className="w-3 h-3" />;
    return <Cpu className="w-3 h-3" />;
  };

  const TypeIcon = ({ type }: { type: string }) => {
    switch (type) {
      case 'image': return <Image className="w-4 h-4 text-purple-500" />;
      case 'link': return <Link className="w-4 h-4 text-blue-500" />;
      case 'file': return <FileText className="w-4 h-4 text-accent" />;
      default: return <Type className="w-4 h-4 text-green-500" />;
    }
  };

  return (
    <div className="min-h-screen bg-cream">
      {/* Header */}
      <div className="bg-white border-b border-border">
        <div className="max-w-2xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/')} className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cream transition">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-lg font-semibold text-text-primary">Share</h1>
              <p className="text-xs text-text-secondary">Drop files, text, or images between devices</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={loadItems} className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cream transition" title="Refresh">
              <RefreshCw className="w-4 h-4" />
            </button>
            {items.length > 0 && (
              <button onClick={clearAll} className="p-2 rounded-lg text-red-400 hover:text-red-600 hover:bg-red-50 transition" title="Clear all">
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-6 space-y-6">
        {/* Device badge */}
        <div className="flex items-center gap-2 text-xs text-text-secondary">
          <DeviceIcon name={device} />
          <span>Sending from <strong className="text-text-primary">{device}</strong></span>
        </div>

        {/* Input area */}
        <div
          className={`bg-white rounded-2xl border-2 border-dashed transition ${dragOver ? 'border-accent bg-accent/5' : 'border-border'}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onPaste={handlePaste}
        >
          <div className="p-4">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); shareText(); } }}
              placeholder="Paste text, error messages, URLs... or drop files here"
              rows={3}
              className="w-full resize-none bg-transparent text-text-primary placeholder:text-text-secondary/50 focus:outline-none text-sm leading-relaxed"
            />
          </div>
          <div className="flex items-center justify-between px-4 pb-3">
            <div className="flex items-center gap-2">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-cream transition"
              >
                <Upload className="w-3.5 h-3.5" /> File
              </button>
              <button
                onClick={async () => {
                  const clip = await navigator.clipboard.readText();
                  if (clip) { setText(clip); }
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-cream transition"
              >
                <Clipboard className="w-3.5 h-3.5" /> Paste clipboard
              </button>
              <input ref={fileInputRef} type="file" multiple className="hidden" onChange={(e) => {
                if (e.target.files) Array.from(e.target.files).forEach(shareFile);
                e.target.value = '';
              }} />
            </div>
            <button
              onClick={shareText}
              disabled={!text.trim() || sending}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-medium transition ${text.trim() && !sending ? 'bg-accent text-white hover:bg-accent-hover' : 'bg-cream text-text-secondary/40 cursor-not-allowed'}`}
            >
              <Send className="w-3.5 h-3.5" /> Share
            </button>
          </div>
        </div>

        {/* Drag hint */}
        {dragOver && (
          <div className="text-center py-4 text-accent text-sm font-medium">
            Drop files here to share
          </div>
        )}

        {/* Items list */}
        {items.length === 0 ? (
          <div className="text-center py-12">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-accent/10 mb-4">
              <Send className="w-7 h-7 text-accent" />
            </div>
            <h3 className="text-text-primary font-medium mb-1">Nothing shared yet</h3>
            <p className="text-sm text-text-secondary">Paste text, drop files, or send screenshots from any device.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <div key={item.id} className="bg-white rounded-xl border border-border p-4 group">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 shrink-0">
                    <TypeIcon type={item.type} />
                  </div>
                  <div className="flex-1 min-w-0">
                    {/* Text/Link content */}
                    {(item.type === 'text' || item.type === 'link') && (
                      <div className="text-sm text-text-primary whitespace-pre-wrap break-words leading-relaxed">
                        {item.type === 'link' ? (
                          <a href={item.content} target="_blank" rel="noopener noreferrer" className="text-accent underline break-all">
                            {item.content}
                          </a>
                        ) : (
                          item.content.length > 500 ? item.content.slice(0, 500) + '...' : item.content
                        )}
                      </div>
                    )}

                    {/* Image */}
                    {item.type === 'image' && item.has_file && (
                      <div className="mb-2">
                        <img
                          src={fileUrl(item.id)}
                          alt={item.filename || 'Shared image'}
                          className="max-w-full max-h-64 rounded-lg border border-border"
                        />
                      </div>
                    )}

                    {/* File info */}
                    {item.type === 'file' && (
                      <div className="flex items-center gap-2 text-sm text-text-primary">
                        <span className="font-medium">{item.filename}</span>
                        <span className="text-text-secondary text-xs">({formatSize(item.file_size)})</span>
                      </div>
                    )}

                    {/* Caption */}
                    {item.content && item.type !== 'text' && item.type !== 'link' && (
                      <p className="text-xs text-text-secondary mt-1">{item.content}</p>
                    )}

                    {/* Meta */}
                    <div className="flex items-center gap-3 mt-2 text-xs text-text-secondary">
                      <span className="flex items-center gap-1">
                        <DeviceIcon name={item.source_device} />
                        {item.source_device || 'Unknown'}
                      </span>
                      <span>{timeAgo(item.created_at)}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition shrink-0">
                    {(item.type === 'text' || item.type === 'link') && (
                      <button onClick={() => copyContent(item)} className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cream transition" title="Copy">
                        {copiedId === item.id ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    )}
                    {item.has_file && (
                      <a href={fileUrl(item.id)} download={item.filename} className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cream transition" title="Download">
                        <Download className="w-3.5 h-3.5" />
                      </a>
                    )}
                    <button onClick={() => deleteItem(item.id)} className="p-1.5 rounded-lg text-text-secondary hover:text-red-500 hover:bg-red-50 transition" title="Delete">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
