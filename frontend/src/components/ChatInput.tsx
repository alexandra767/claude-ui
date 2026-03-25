import { useState, useRef, useEffect, useCallback } from 'react';
import { ArrowUp, Paperclip, X, Globe, Code, FileText, ChevronDown } from 'lucide-react';
import Editor from 'react-simple-code-editor';
import Prism from 'prismjs';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-typescript';
import 'prismjs/components/prism-swift';
import 'prismjs/components/prism-bash';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-css';
import 'prismjs/themes/prism-tomorrow.css';
import { useChatStore } from '../stores/chatStore';
import { files } from '../api/client';
import type { Attachment } from '../types';

interface Props {
  onSend: (message: string, attachments?: Attachment[]) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState('');
  const [codeMode, setCodeMode] = useState(false);
  const [codeLang, setCodeLang] = useState('python');
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const LANGUAGES = ['python', 'javascript', 'typescript', 'swift', 'bash', 'json', 'css'];

  const highlightCode = useCallback((code: string) => {
    const grammar = Prism.languages[codeLang] || Prism.languages.python;
    return Prism.highlight(code, grammar, codeLang);
  }, [codeLang]);
  const isStreaming = useChatStore((s) => s.isStreaming);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = () => {
    if (!text.trim() && attachments.length === 0) return;
    if (disabled || isStreaming) return;
    // Wrap code in markdown code block when in code mode
    const message = codeMode && text.trim() ? `\`\`\`${codeLang}\n${text.trim()}\n\`\`\`` : text.trim();
    onSend(message, attachments.length > 0 ? attachments : undefined);
    setText('');
    setAttachments([]);
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList) return;
    setUploading(true);
    try {
      for (const file of Array.from(fileList)) {
        const result = await files.upload(file);
        setAttachments((prev) => [...prev, result]);
      }
    } catch {}
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Paste images directly (Cmd+V)
  const handlePaste = async (e: React.ClipboardEvent) => {
    const items = e.clipboardData.items;
    for (const item of Array.from(items)) {
      if (item.type.startsWith('image/')) {
        e.preventDefault();
        const file = item.getAsFile();
        if (!file) continue;
        setUploading(true);
        try {
          const result = await files.upload(file);
          setAttachments((prev) => [...prev, result]);
        } catch {}
        setUploading(false);
        return;
      }
    }
  };

  const removeAttachment = (idx: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 200) + 'px';
    }
  };

  const canSend = (text.trim() || attachments.length > 0) && !disabled && !isStreaming;

  return (
    <div className="w-full max-w-3xl mx-auto px-2 sm:px-4 pb-2 sm:pb-4">
      <div className="bg-white rounded-2xl border border-border shadow-sm">
        {/* Attachments */}
        {attachments.length > 0 && (
          <div className="flex gap-2 px-4 pt-3 flex-wrap">
            {attachments.map((a, i) => (
              <div key={i} className="flex items-center gap-2 bg-cream rounded-lg px-3 py-1.5 text-sm text-text-primary">
                <FileText className="w-3.5 h-3.5 text-text-secondary" />
                <span className="max-w-[150px] truncate">{a.filename}</span>
                <button onClick={() => removeAttachment(i)} className="text-text-secondary hover:text-red-500 transition">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Input area */}
        <div className="flex items-end gap-2 p-3">
          <div className="flex items-center gap-1">
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cream transition"
              title="Attach file"
            >
              <Paperclip className="w-5 h-5" />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={handleFileUpload}
              className="hidden"
            />
            <button
              onClick={() => setCodeMode(!codeMode)}
              className={`p-2 rounded-lg transition ${codeMode ? 'text-accent bg-accent/10' : 'text-text-secondary hover:text-text-primary hover:bg-cream'}`}
              title={codeMode ? 'Switch to text' : 'Switch to code editor'}
            >
              <Code className="w-5 h-5" />
            </button>
          </div>

          {codeMode ? (
            <div className="flex-1 rounded-lg bg-[#1e1e1e] overflow-hidden max-h-[300px] overflow-y-auto">
              {/* Language selector */}
              <div className="flex items-center justify-between px-3 py-1 bg-[#2d2d2d] text-[#999] text-xs">
                <select
                  value={codeLang}
                  onChange={(e) => setCodeLang(e.target.value)}
                  className="bg-transparent text-[#ccc] text-xs focus:outline-none cursor-pointer"
                >
                  {LANGUAGES.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
                <span className="text-[#666]">Code Mode</span>
              </div>
              <Editor
                value={text}
                onValueChange={setText}
                highlight={highlightCode}
                padding={12}
                onKeyDown={(e: React.KeyboardEvent) => {
                  if (e.key === 'Enter' && !e.shiftKey && e.metaKey) { e.preventDefault(); handleSubmit(); }
                }}
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '14px',
                  lineHeight: '1.6',
                  minHeight: '60px',
                  color: '#d4d4d4',
                }}
                placeholder="Write your code here..."
                textareaClassName="code-editor-textarea"
              />
            </div>
          ) : (
            <textarea
              ref={textareaRef}
              value={text}
              onChange={(e) => { setText(e.target.value); handleInput(); }}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              placeholder="Message..."
              rows={1}
              className="flex-1 resize-none bg-transparent text-text-primary placeholder:text-text-secondary/60 focus:outline-none text-[16px] leading-6 py-2 max-h-[200px]"
            />
          )}

          <button
            onClick={handleSubmit}
            disabled={!canSend}
            className={`p-2 rounded-xl transition ${canSend ? 'bg-accent text-white hover:bg-accent-hover' : 'bg-cream text-text-secondary/40 cursor-not-allowed'}`}
          >
            <ArrowUp className="w-5 h-5" />
          </button>
        </div>

        {/* Bottom bar */}
        <div className="flex items-center justify-between px-4 pb-2 pt-0">
          <ModelBadge />
          <span className="text-xs text-text-secondary/50">
            {isStreaming ? 'Generating...' : 'Enter to send, Shift+Enter for new line'}
          </span>
        </div>
      </div>
    </div>
  );
}

function ModelBadge() {
  const { selectedModel, setSelectedModel } = useChatStore();
  const [showPicker, setShowPicker] = useState(false);
  const [models, setModels] = useState<string[]>([]);

  const loadModels = async () => {
    try {
      const { chat: chatApi } = await import('../api/client');
      const data = await chatApi.getModels();
      setModels(data.models);
    } catch {}
  };

  return (
    <div className="relative">
      <button
        onClick={() => { setShowPicker(!showPicker); if (!showPicker) loadModels(); }}
        className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary transition px-2 py-1 rounded-md hover:bg-cream"
      >
        <Sparkle className="w-3 h-3" />
        <span>{selectedModel}</span>
      </button>
      {showPicker && models.length > 0 && (
        <div className="absolute bottom-full left-0 mb-1 bg-white rounded-xl border border-border shadow-lg py-1 min-w-[200px] max-h-[200px] overflow-y-auto z-50">
          {models.map((m) => (
            <button
              key={m}
              onClick={() => { setSelectedModel(m); setShowPicker(false); }}
              className={`w-full text-left px-3 py-2 text-sm hover:bg-cream transition ${m === selectedModel ? 'text-accent font-medium' : 'text-text-primary'}`}
            >
              {m}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Sparkle({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="currentColor">
      <path d="M8 0l1.5 5.5L15 7l-5.5 1.5L8 14l-1.5-5.5L1 7l5.5-1.5z" />
    </svg>
  );
}
