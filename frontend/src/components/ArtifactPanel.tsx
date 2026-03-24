import { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import vscDarkPlus from 'react-syntax-highlighter/dist/esm/styles/prism/vsc-dark-plus';
import { useChatStore } from '../stores/chatStore';
import { X, Copy, Check, Code, Eye, Download, Maximize2, Minimize2 } from 'lucide-react';

export default function ArtifactPanel() {
  const { activeArtifact, setActiveArtifact, showArtifactPanel } = useChatStore();
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview');
  const [copied, setCopied] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);

  if (!showArtifactPanel || !activeArtifact) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(activeArtifact.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const ext = getExtension(activeArtifact.type, activeArtifact.language);
    const blob = new Blob([activeArtifact.content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${activeArtifact.title.replace(/\s+/g, '_').toLowerCase()}${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const canPreview = ['html', 'svg', 'mermaid'].includes(activeArtifact.type);

  return (
    <div className={`bg-white border-l border-border flex flex-col ${fullscreen ? 'fixed inset-0 z-50 border-none' : 'w-[500px]'}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-accent/10 flex items-center justify-center text-accent text-xs font-bold">
            {activeArtifact.type === 'html' ? '</>' : '#'}
          </div>
          <div className="min-w-0">
            <div className="text-sm font-medium text-text-primary truncate">{activeArtifact.title}</div>
            <div className="text-xs text-text-secondary">{activeArtifact.language || activeArtifact.type}</div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {canPreview && (
            <div className="flex items-center bg-cream rounded-lg p-0.5 mr-2">
              <button
                onClick={() => setViewMode('preview')}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${viewMode === 'preview' ? 'bg-white shadow-sm text-text-primary' : 'text-text-secondary hover:text-text-primary'}`}
              >
                <Eye className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setViewMode('code')}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${viewMode === 'code' ? 'bg-white shadow-sm text-text-primary' : 'text-text-secondary hover:text-text-primary'}`}
              >
                <Code className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
          <button onClick={handleCopy} className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cream transition" title="Copy">
            {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
          </button>
          <button onClick={handleDownload} className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cream transition" title="Download">
            <Download className="w-4 h-4" />
          </button>
          <button onClick={() => setFullscreen(!fullscreen)} className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cream transition" title="Fullscreen">
            {fullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          <button onClick={() => setActiveArtifact(null)} className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cream transition" title="Close">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {canPreview && viewMode === 'preview' ? (
          <ArtifactPreview type={activeArtifact.type} content={activeArtifact.content} />
        ) : (
          <SyntaxHighlighter
            language={activeArtifact.language || activeArtifact.type || 'text'}
            style={vscDarkPlus}
            showLineNumbers
            lineNumberStyle={{ color: '#555', fontSize: '0.75rem', paddingRight: '1em', minWidth: '2.5em' }}
            customStyle={{ margin: 0, borderRadius: 0, fontSize: '0.875rem', lineHeight: '1.6', height: '100%' }}
          >
            {activeArtifact.content}
          </SyntaxHighlighter>
        )}
      </div>
    </div>
  );
}

function ArtifactPreview({ type, content }: { type: string; content: string }) {
  if (type === 'html') {
    return (
      <iframe
        srcDoc={content}
        className="w-full h-full border-none"
        sandbox="allow-scripts allow-same-origin"
        title="HTML Preview"
      />
    );
  }
  if (type === 'svg') {
    return (
      <div className="p-6 flex items-center justify-center" dangerouslySetInnerHTML={{ __html: content }} />
    );
  }
  return (
    <pre className="p-4 text-sm font-mono text-text-primary whitespace-pre-wrap">{content}</pre>
  );
}

function getExtension(type: string, language?: string): string {
  if (type === 'html') return '.html';
  if (type === 'svg') return '.svg';
  if (type === 'mermaid') return '.mmd';
  const langMap: Record<string, string> = {
    python: '.py', javascript: '.js', typescript: '.ts', java: '.java',
    cpp: '.cpp', c: '.c', rust: '.rs', go: '.go', ruby: '.rb',
    css: '.css', json: '.json', yaml: '.yml', sql: '.sql',
    bash: '.sh', shell: '.sh', markdown: '.md',
  };
  return langMap[language || ''] || '.txt';
}
