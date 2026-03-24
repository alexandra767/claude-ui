import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import vscDarkPlus from 'react-syntax-highlighter/dist/esm/styles/prism/vsc-dark-plus';
import { useChatStore } from '../stores/chatStore';
import { Copy, Check, User, Sparkles, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import type { Message, Artifact } from '../types';

interface Props {
  message: Message;
  isStreaming?: boolean;
  streamContent?: string;
}

export default function MessageBubble({ message, isStreaming, streamContent }: Props) {
  const content = isStreaming ? streamContent || '' : message.content;
  const isUser = message.role === 'user';
  const setActiveArtifact = useChatStore((s) => s.setActiveArtifact);

  return (
    <div className={`flex gap-4 py-6 px-4 ${isUser ? '' : ''}`}>
      {/* Avatar */}
      <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${isUser ? 'bg-accent/15 text-accent' : 'bg-gradient-to-br from-accent/20 to-orange-200 text-accent'}`}>
        {isUser ? <User className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="text-xs font-medium text-text-secondary mb-1.5">
          {isUser ? 'You' : 'Assistant'}
        </div>

        {/* Attachments */}
        {message.attachments && message.attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {message.attachments.map((a, i) => (
              <div key={i} className="flex items-center gap-2 bg-cream-dark rounded-lg px-3 py-1.5 text-sm text-text-secondary">
                <span>{a.filename}</span>
                <span className="text-xs">({formatSize(a.size)})</span>
              </div>
            ))}
          </div>
        )}

        {/* Message content */}
        {isUser ? (
          <div className="text-text-primary leading-relaxed whitespace-pre-wrap">{content}</div>
        ) : (
          <div className={`markdown-content text-text-primary ${isStreaming ? 'streaming-cursor' : ''}`}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const codeStr = String(children).replace(/\n$/, '');
                  if (match) {
                    return <CodeBlock language={match[1]} code={codeStr} />;
                  }
                  return <code className={className} {...props}>{children}</code>;
                },
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        )}

        {/* Artifacts */}
        {message.artifacts && message.artifacts.length > 0 && (
          <div className="mt-3 space-y-2">
            {message.artifacts.map((artifact) => (
              <button
                key={artifact.id}
                onClick={() => setActiveArtifact(artifact)}
                className="flex items-center gap-3 w-full text-left bg-white border border-border rounded-xl px-4 py-3 hover:border-accent/40 hover:shadow-sm transition group"
              >
                <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center text-accent">
                  <ArtifactIcon type={artifact.type} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-text-primary truncate">{artifact.title}</div>
                  <div className="text-xs text-text-secondary">{artifact.type}</div>
                </div>
                <ChevronRight className="w-4 h-4 text-text-secondary group-hover:text-accent transition" />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group my-3 rounded-xl overflow-hidden border border-border/50">
      <div className="flex items-center justify-between px-4 py-2 bg-[#2d2d2d] text-[#999] text-xs">
        <span>{language}</span>
        <button onClick={handleCopy} className="flex items-center gap-1 hover:text-white transition">
          {copied ? <><Check className="w-3.5 h-3.5" /> Copied</> : <><Copy className="w-3.5 h-3.5" /> Copy</>}
        </button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={vscDarkPlus}
        customStyle={{ margin: 0, borderRadius: 0, fontSize: '0.875rem', lineHeight: '1.6' }}
        showLineNumbers
        lineNumberStyle={{ color: '#555', fontSize: '0.75rem', paddingRight: '1em', minWidth: '2.5em' }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

function ArtifactIcon({ type }: { type: string }) {
  switch (type) {
    case 'html': return <span className="text-xs font-bold">&lt;/&gt;</span>;
    case 'svg': return <span className="text-xs font-bold">SVG</span>;
    case 'mermaid': return <span className="text-xs font-bold">M</span>;
    default: return <span className="text-xs font-bold">#</span>;
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}
