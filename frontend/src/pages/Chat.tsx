import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useChatStore } from '../stores/chatStore';
import { chat as chatApi } from '../api/client';
import Sidebar from '../components/Sidebar';
import ChatInput from '../components/ChatInput';
import MessageBubble from '../components/MessageBubble';
import ArtifactPanel from '../components/ArtifactPanel';
import { Menu, Sparkles, Zap, Terminal, Search, Globe, Mail, Calendar, Calculator, Clock, FileCode, Image as ImageIcon, Square, ChevronDown, ChevronRight, Brain } from 'lucide-react';
import type { Message, Attachment } from '../types';
import { useToastStore } from '../stores/toastStore';

interface StreamStats {
  tokens: number;
  tokensPerSec: number;
  duration: number;
}

interface ActiveTool {
  name: string;
  status: 'running' | 'done';
  result?: any;
}

const TOOL_META: Record<string, { label: string; icon: typeof Terminal }> = {
  execute_code: { label: 'Running code', icon: Terminal },
  web_search: { label: 'Searching the web', icon: Search },
  fetch_url: { label: 'Reading webpage', icon: Globe },
  gmail_search: { label: 'Searching emails', icon: Mail },
  gmail_read: { label: 'Reading email', icon: Mail },
  gmail_send: { label: 'Sending email', icon: Mail },
  calendar_list: { label: 'Checking calendar', icon: Calendar },
  calendar_create: { label: 'Creating event', icon: Calendar },
  get_weather: { label: 'Getting weather', icon: Globe },
  get_datetime: { label: 'Getting date/time', icon: Clock },
  calculator: { label: 'Calculating', icon: Calculator },
  create_artifact: { label: 'Creating artifact', icon: FileCode },
  generate_image: { label: 'Generating image', icon: ImageIcon },
  edit_image: { label: 'Editing image', icon: ImageIcon },
};

export default function Chat() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get('project') || undefined;
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [streamStats, setStreamStats] = useState<StreamStats | null>(null);
  const [liveTokenCount, setLiveTokenCount] = useState(0);
  const [liveTps, setLiveTps] = useState(0);
  const [activeTools, setActiveTools] = useState<ActiveTool[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [thinkingContent, setThinkingContent] = useState('');
  const streamStartRef = useRef<number>(0);
  const tokenCountRef = useRef<number>(0);
  const abortControllerRef = useRef<AbortController | null>(null);

  const {
    activeConversationId, setActiveConversation, messages, setMessages,
    addMessage, isStreaming, setStreaming, streamingContent,
    appendStreamContent, resetStreamContent, selectedModel, selectedPersona,
    showArtifactPanel, setConversations,
  } = useChatStore();

  // Load conversation if URL has ID
  useEffect(() => {
    if (conversationId && conversationId !== activeConversationId) {
      setActiveConversation(conversationId);
      chatApi.getConversation(conversationId).then((data) => {
        setMessages(data.messages || []);
      }).catch(() => {
        useToastStore.getState().addToast('Failed to load conversation', 'error');
        navigate('/chat');
      });
    } else if (!conversationId) {
      setActiveConversation(null);
      setMessages([]);
    }
  }, [conversationId]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Swipe to open sidebar on mobile
  useEffect(() => {
    let startX = 0;
    let startY = 0;
    const onStart = (e: TouchEvent) => { startX = e.touches[0].clientX; startY = e.touches[0].clientY; };
    const onEnd = (e: TouchEvent) => {
      const dx = e.changedTouches[0].clientX - startX;
      const dy = Math.abs(e.changedTouches[0].clientY - startY);
      if (dx > 80 && dy < 50 && startX < 30) setSidebarOpen(true);  // Swipe right from left edge
      if (dx < -80 && dy < 50) setSidebarOpen(false);  // Swipe left to close
    };
    window.addEventListener('touchstart', onStart, { passive: true });
    window.addEventListener('touchend', onEnd, { passive: true });
    return () => { window.removeEventListener('touchstart', onStart); window.removeEventListener('touchend', onEnd); };
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key === 'n') { e.preventDefault(); setActiveConversation(null); setMessages([]); navigate('/chat'); }
      if (mod && e.key === 'k') { e.preventDefault(); document.querySelector<HTMLInputElement>('[placeholder*="Search"]')?.focus(); }
      if (mod && e.shiftKey && e.key === 'S') { e.preventDefault(); setSidebarOpen(prev => !prev); }
      if (e.key === 'Escape') { if (showArtifactPanel) useChatStore.getState().setShowArtifactPanel(false); }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, []);

  const handleSend = async (text: string, attachments?: Attachment[]) => {
    // Add user message optimistically
    const userMsg: Message = {
      id: 'temp-' + Date.now(),
      role: 'user',
      content: text,
      attachments,
      created_at: new Date().toISOString(),
    };
    addMessage(userMsg);

    // Start streaming
    setStreaming(true);
    resetStreamContent();
    setStreamStats(null);
    setLiveTokenCount(0);
    setLiveTps(0);
    setActiveTools([]);
    setIsThinking(false);
    setThinkingContent('');
    abortControllerRef.current = new AbortController();
    streamStartRef.current = Date.now();
    tokenCountRef.current = 0;

    try {
      const response = await chatApi.sendMessage({
        conversation_id: activeConversationId || undefined,
        message: text,
        model: selectedModel,
        project_id: projectId,
        persona: selectedPersona !== 'default' ? selectedPersona : undefined,
        attachments,
      });

      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';
      let newConvoId = activeConversationId;
      let artifacts: any[] = [];
      let generatedImages: { filename: string; prompt: string }[] = [];
      let thinkingText = '';
      let ollamaEvalCount = 0;
      let ollamaEvalDuration = 0;

      while (true) {
        const readResult = await Promise.race([
          reader.read(),
          new Promise<never>((_, reject) =>
            setTimeout(() => reject(new Error("Stream timeout — no data received for 180 seconds. Use the regenerate button (↻) to retry, or check that Ollama is running.")), 180000)
          ),
        ]);
        const { done, value } = readResult;
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            switch (data.type) {
              case 'thinking':
                setIsThinking(true);
                thinkingText += data.content;
                setThinkingContent(thinkingText);
                break;
              case 'token':
                setIsThinking(false);
                fullContent += data.content;
                appendStreamContent(data.content);
                tokenCountRef.current++;
                const elapsed = (Date.now() - streamStartRef.current) / 1000;
                setLiveTokenCount(tokenCountRef.current);
                setLiveTps(elapsed > 0 ? tokenCountRef.current / elapsed : 0);
                break;
              case 'metrics':
                ollamaEvalCount += (data.eval_count || 0);
                ollamaEvalDuration += (data.eval_duration || 0);
                break;
              case 'tool_start':
                setActiveTools(prev => [...prev, { name: data.name, status: 'running' }]);
                break;
              case 'tool_result':
                setActiveTools(prev => prev.map(t =>
                  t.name === data.name && t.status === 'running'
                    ? { ...t, status: 'done', result: data.result }
                    : t
                ));
                break;
              case 'image':
                generatedImages.push({ filename: data.filename, prompt: data.prompt || '' });
                break;
              case 'artifact':
                artifacts.push(data.artifact);
                break;
              case 'artifacts':
                artifacts.push(...data.artifacts);
                break;
              case 'done':
                newConvoId = data.conversation_id;
                break;
              case 'error':
                fullContent += `\n\n**Error:** ${data.content}`;
                appendStreamContent(`\n\n**Error:** ${data.content}`);
                break;
            }
          } catch {}
        }
      }

      // Calculate final stats — prefer Ollama's precise numbers
      const totalDuration = (Date.now() - streamStartRef.current) / 1000;
      const finalTokens = ollamaEvalCount || tokenCountRef.current;
      const finalTps = ollamaEvalDuration > 0
        ? ollamaEvalCount / (ollamaEvalDuration / 1e9)
        : (totalDuration > 0 ? finalTokens / totalDuration : 0);
      setStreamStats({ tokens: finalTokens, tokensPerSec: finalTps, duration: totalDuration });

      // Add assistant message
      const assistantMsg: Message = {
        id: 'msg-' + Date.now(),
        role: 'assistant',
        content: fullContent,
        model: selectedModel,
        artifacts: artifacts.length > 0 ? artifacts : undefined,
        images: generatedImages.length > 0 ? generatedImages : undefined,
        thinking: thinkingText || undefined,
        created_at: new Date().toISOString(),
      };
      addMessage(assistantMsg);

      // Navigate to new conversation if created
      if (newConvoId && newConvoId !== activeConversationId) {
        setActiveConversation(newConvoId);
        navigate(`/chat/${newConvoId}`, { replace: true });
        // Refresh sidebar
        chatApi.listConversations().then(setConversations).catch(() => {
          useToastStore.getState().addToast('Failed to refresh conversations', 'warning');
        });
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        // Preserve any partial streaming content
        const partial = useChatStore.getState().streamingContent;
        if (partial) {
          addMessage({
            id: 'msg-' + Date.now(),
            role: 'assistant',
            content: partial + '\n\n---\n*Connection lost — response may be incomplete. Use the regenerate button (↻) to retry.*',
            created_at: new Date().toISOString(),
          });
        } else {
          addMessage({
            id: 'err-' + Date.now(),
            role: 'assistant',
            content: `Connection lost: ${err.message}. Use the regenerate button (↻) to retry, or check that Ollama is running.`,
            created_at: new Date().toISOString(),
          });
        }
      }
    } finally {
      setStreaming(false);
      resetStreamContent();
      abortControllerRef.current = null;
    }
  };

  const handleStop = () => {
    abortControllerRef.current?.abort();
    setStreaming(false);
    resetStreamContent();
  };

  const handleEdit = async (msg: Message) => {
    if (!activeConversationId) return;
    // Delete this message and everything after it
    try {
      const token = localStorage.getItem('token');
      await fetch(`/api/chat/conversations/${activeConversationId}/messages/${msg.id}`, {
        method: 'DELETE',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      // Reload conversation
      const data = await chatApi.getConversation(activeConversationId);
      setMessages(data.messages || []);
      // Put the old message text into the input (user can edit it)
      const input = document.querySelector<HTMLTextAreaElement>('textarea');
      if (input) { input.value = msg.content; input.focus(); input.dispatchEvent(new Event('input', { bubbles: true })); }
    } catch {
      useToastStore.getState().addToast('Failed to edit message', 'error');
    }
  };

  const handleRegenerate = async (msg: Message) => {
    if (!activeConversationId || messages.length < 2) return;
    // Find the user message before this assistant message
    const idx = messages.findIndex(m => m.id === msg.id);
    if (idx < 1) return;
    const userMsg = messages[idx - 1];
    // Delete the assistant message
    try {
      const token = localStorage.getItem('token');
      await fetch(`/api/chat/conversations/${activeConversationId}/messages/${msg.id}`, {
        method: 'DELETE',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      // Reload and resend
      const data = await chatApi.getConversation(activeConversationId);
      setMessages(data.messages || []);
      // Re-send the user's message
      handleSend(userMsg.content, userMsg.attachments);
    } catch {
      useToastStore.getState().addToast('Failed to regenerate response', 'error');
    }
  };

  const isEmpty = messages.length === 0 && !isStreaming;

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex overflow-hidden">
        {/* Main chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Top bar */}
          <div className="flex items-center gap-3 px-3 sm:px-4 py-2 sm:py-3 border-b border-border bg-white/50 backdrop-blur-sm">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cream transition"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2 text-sm text-text-secondary">
              <Sparkles className="w-4 h-4 text-accent" />
              <span className="font-medium text-text-primary">{selectedModel}</span>
            </div>
            {projectId && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-accent/10 text-accent text-xs font-medium">
                <span className="w-2 h-2 rounded-full bg-accent" />
                Project mode
              </div>
            )}
          </div>

          {/* Messages area — supports drag-drop files */}
          <div
            className={`flex-1 overflow-y-auto ${dragOver ? 'ring-2 ring-accent ring-inset bg-accent/5' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={async (e) => {
              e.preventDefault();
              setDragOver(false);
              const { files: fileApi } = await import('../api/client');
              for (const file of Array.from(e.dataTransfer.files)) {
                try {
                  await fileApi.upload(file);
                } catch {
                  useToastStore.getState().addToast('Failed to upload file', 'error');
                }
              }
            }}
          >
            {isEmpty ? (
              <EmptyState onSend={handleSend} />
            ) : (
              <div className="max-w-3xl mx-auto">
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} onEdit={handleEdit} onRegenerate={handleRegenerate} />
                ))}
                {isStreaming && (
                  <>
                    {/* Thinking block */}
                    {isThinking && activeTools.length === 0 && (
                      <ThinkingBlock content={thinkingContent} isLive />
                    )}
                    {/* Tool activity indicators */}
                    {activeTools.length > 0 && (
                      <div className="px-6 sm:px-16 py-2 space-y-1.5">
                        {activeTools.map((tool, i) => {
                          const meta = TOOL_META[tool.name] || { label: tool.name, icon: Terminal };
                          const Icon = meta.icon;
                          return (
                            <div key={i} className={`flex items-center gap-2 text-xs rounded-lg px-3 py-2 ${tool.status === 'running' ? 'bg-accent/5 text-accent' : 'bg-green-50 text-green-600'}`}>
                              <Icon className="w-3.5 h-3.5" />
                              <span className="font-medium">{meta.label}</span>
                              {tool.status === 'running' && (
                                <span className="flex gap-0.5 ml-1">
                                  <span className="w-1 h-1 rounded-full bg-accent thinking-dot" />
                                  <span className="w-1 h-1 rounded-full bg-accent thinking-dot" />
                                  <span className="w-1 h-1 rounded-full bg-accent thinking-dot" />
                                </span>
                              )}
                              {tool.status === 'done' && <span className="ml-1">Done</span>}
                            </div>
                          );
                        })}
                      </div>
                    )}
                    <MessageBubble
                      message={{ id: 'streaming', role: 'assistant', content: '', created_at: '' }}
                      isStreaming
                      streamContent={streamingContent}
                    />
                    {liveTokenCount > 0 && (
                      <div className="flex items-center gap-2 px-6 sm:px-16 pb-2 text-xs text-text-secondary">
                        <Zap className="w-3 h-3 text-accent" />
                        <span>{liveTps.toFixed(1)} tokens/s</span>
                        <span className="text-text-secondary/40">|</span>
                        <span>{liveTokenCount} tokens</span>
                      </div>
                    )}
                  </>
                )}
                {!isStreaming && streamStats && messages.length > 0 && messages[messages.length - 1].role === 'assistant' && (
                  <div className="flex items-center gap-2 px-6 sm:px-16 pb-2 text-xs text-text-secondary">
                    <Zap className="w-3 h-3 text-green-500" />
                    <span className="font-medium">{streamStats.tokensPerSec.toFixed(1)} tokens/s</span>
                    <span className="text-text-secondary/40">|</span>
                    <span>{streamStats.tokens.toLocaleString()} tokens</span>
                    <span className="text-text-secondary/40">|</span>
                    <span>{streamStats.duration.toFixed(1)}s</span>
                  </div>
                )}
                <div ref={messagesEndRef} className="h-4" />
              </div>
            )}
          </div>

          {/* Stop button */}
          {isStreaming && (
            <div className="flex justify-center py-2">
              <button
                onClick={handleStop}
                className="flex items-center gap-2 px-4 py-2 rounded-xl border border-border bg-white text-text-secondary text-sm hover:bg-cream hover:text-text-primary transition"
              >
                <Square className="w-3.5 h-3.5 fill-current" /> Stop generating
              </button>
            </div>
          )}

          {/* Input */}
          <ChatInput onSend={handleSend} />
        </div>

        {/* Artifact panel */}
        {showArtifactPanel && <ArtifactPanel />}
      </div>
    </div>
  );
}

function EmptyState({ onSend }: { onSend: (msg: string) => void }) {
  const suggestions = [
    'What\'s the weather like today?',
    'Check my calendar for this week',
    'Write a Python script',
    'Search my recent emails',
  ];
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center max-w-md px-4">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-accent/15 to-orange-100 mb-6">
          <Sparkles className="w-8 h-8 text-accent" />
        </div>
        <h2 className="text-xl font-semibold text-text-primary mb-2">How can I help you today?</h2>
        <p className="text-text-secondary text-sm leading-relaxed">
          I can search the web, run code, check your email and calendar, and more.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-6">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onSend(s)}
              className="text-left px-4 py-3 rounded-xl border border-border text-sm text-text-secondary hover:bg-white hover:border-accent/30 hover:text-text-primary transition"
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function ThinkingBlock({ content, isLive }: { content: string; isLive?: boolean }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="px-6 sm:px-16 py-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition"
      >
        <Brain className="w-4 h-4 text-accent" />
        <span className="font-medium">
          {isLive ? 'Thinking' : 'Thought process'}
        </span>
        {isLive && (
          <span className="flex gap-0.5 ml-1">
            <span className="w-1.5 h-1.5 rounded-full bg-accent thinking-dot" />
            <span className="w-1.5 h-1.5 rounded-full bg-accent thinking-dot" />
            <span className="w-1.5 h-1.5 rounded-full bg-accent thinking-dot" />
          </span>
        )}
        {expanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        {!expanded && content && (
          <span className="text-xs text-text-secondary/60 truncate max-w-[300px]">
            {content.slice(0, 80)}...
          </span>
        )}
      </button>
      {expanded && content && (
        <div className="mt-2 ml-6 pl-3 border-l-2 border-accent/20 text-sm text-text-secondary leading-relaxed whitespace-pre-wrap max-h-[300px] overflow-y-auto">
          {content}
        </div>
      )}
    </div>
  );
}
