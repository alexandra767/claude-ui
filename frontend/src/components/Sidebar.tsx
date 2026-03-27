import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useChatStore } from '../stores/chatStore';
import { useAuthStore } from '../stores/authStore';
import { chat } from '../api/client';
import {
  Plus, Search, MessageSquare, Star, Trash2, Pencil, Check, X,
  Settings, FolderOpen, LogOut, ChevronDown, Sparkles, Send, Download, Image
} from 'lucide-react';
import type { Conversation } from '../types';
import { useToastStore } from '../stores/toastStore';

export default function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { conversations, setConversations, activeConversationId, setActiveConversation, setMessages, removeConversation, updateConversation } = useChatStore();
  const { user, logout } = useAuthStore();
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [showUserMenu, setShowUserMenu] = useState(false);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const convos = await chat.listConversations();
      setConversations(convos);
    } catch {
      useToastStore.getState().addToast('Failed to load conversations', 'error');
    }
  };

  const startNewChat = () => {
    setActiveConversation(null);
    setMessages([]);
    navigate('/chat');
    onClose();
  };

  const openConversation = async (convo: Conversation) => {
    setActiveConversation(convo.id);
    navigate(`/chat/${convo.id}`);
    onClose();
    try {
      const full = await chat.getConversation(convo.id);
      setMessages(full.messages || []);
    } catch {
      useToastStore.getState().addToast('Failed to load conversation', 'error');
    }
  };

  const deleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await chat.deleteConversation(id);
      removeConversation(id);
    } catch {
      useToastStore.getState().addToast('Failed to delete conversation', 'error');
    }
  };

  const toggleStar = async (convo: Conversation, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await chat.updateConversation(convo.id, { is_starred: !convo.is_starred });
      updateConversation(convo.id, { is_starred: !convo.is_starred });
    } catch {
      useToastStore.getState().addToast('Failed to update conversation', 'warning');
    }
  };

  const exportConversation = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const token = localStorage.getItem('token');
    window.open(`/api/chat/conversations/${id}/export?token=${token}`, '_blank');
  };

  // Content search with debounce
  useEffect(() => {
    if (search.length < 2) { setSearchResults([]); return; }
    const timer = setTimeout(async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`/api/chat/search?q=${encodeURIComponent(search)}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (res.ok) setSearchResults(await res.json());
      } catch {
        useToastStore.getState().addToast('Search failed', 'warning');
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const startRename = (convo: Conversation, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(convo.id);
    setEditTitle(convo.title);
  };

  const saveRename = async (id: string) => {
    if (editTitle.trim()) {
      try {
        await chat.updateConversation(id, { title: editTitle.trim() });
        updateConversation(id, { title: editTitle.trim() });
      } catch {
        useToastStore.getState().addToast('Failed to rename conversation', 'error');
      }
    }
    setEditingId(null);
  };

  const filtered = conversations.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase())
  );
  const starred = filtered.filter((c) => c.is_starred && !c.project_id);
  const projectChats = filtered.filter((c) => c.project_id);
  const recent = filtered.filter((c) => !c.is_starred && !c.project_id);

  // Group recent by calendar day (local timezone)
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(startOfToday.getTime() - 86400000);
  const startOfWeek = new Date(startOfToday.getTime() - 6 * 86400000);
  const groups: { label: string; items: Conversation[] }[] = [];
  const todayItems: Conversation[] = [];
  const yesterdayItems: Conversation[] = [];
  const weekItems: Conversation[] = [];
  const olderItems: Conversation[] = [];

  recent.forEach((c) => {
    const d = new Date(c.updated_at);
    if (d >= startOfToday) todayItems.push(c);
    else if (d >= startOfYesterday) yesterdayItems.push(c);
    else if (d >= startOfWeek) weekItems.push(c);
    else olderItems.push(c);
  });

  if (todayItems.length) groups.push({ label: 'Today', items: todayItems });
  if (yesterdayItems.length) groups.push({ label: 'Yesterday', items: yesterdayItems });
  if (weekItems.length) groups.push({ label: 'This Week', items: weekItems });
  if (olderItems.length) groups.push({ label: 'Older', items: olderItems });

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={onClose} />}

      <aside className={`fixed lg:relative z-50 h-full w-72 bg-sidebar-bg flex flex-col transition-transform duration-300 ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
        {/* Header */}
        <div className="p-3 flex items-center gap-2">
          <button
            onClick={startNewChat}
            className="flex-1 flex items-center gap-2 px-3 py-2.5 rounded-xl text-text-sidebar hover:bg-sidebar-hover transition text-sm font-medium"
          >
            <Sparkles className="w-4 h-4" />
            <span>New chat</span>
          </button>
          <button
            onClick={startNewChat}
            className="p-2.5 rounded-xl text-text-sidebar hover:bg-sidebar-hover transition"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {/* Search */}
        <div className="px-3 mb-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-sidebar-dim" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search conversations..."
              className="w-full pl-9 pr-3 py-2 rounded-lg bg-sidebar-hover text-text-sidebar text-sm placeholder:text-text-sidebar-dim focus:outline-none focus:ring-1 focus:ring-accent/40"
            />
          </div>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto sidebar-scroll px-2 space-y-1">
          {/* Content search results */}
          {searchResults.length > 0 && search.length >= 2 && (
            <div className="mb-3">
              <div className="px-2 py-1 text-xs font-medium text-text-sidebar-dim uppercase tracking-wider">Search Results</div>
              {searchResults.map((r: any) => (
                <div
                  key={r.message_id}
                  onClick={() => { navigate(`/chat/${r.conversation_id}`); onClose(); setSearch(''); setSearchResults([]); }}
                  className="px-2 py-2 rounded-lg cursor-pointer text-sm text-text-sidebar-dim hover:bg-sidebar-hover hover:text-text-sidebar transition"
                >
                  <div className="text-text-sidebar truncate text-xs font-medium">{r.conversation_title}</div>
                  <div className="text-text-sidebar-dim text-xs truncate mt-0.5">{r.snippet.slice(0, 80)}...</div>
                </div>
              ))}
            </div>
          )}
          {/* Starred */}
          {starred.length > 0 && (
            <div className="mb-3">
              <div className="px-2 py-1 text-xs font-medium text-text-sidebar-dim uppercase tracking-wider">Starred</div>
              {starred.map((c) => renderConvoItem(c))}
            </div>
          )}

          {/* Date groups */}
          {groups.map((g) => (
            <div key={g.label} className="mb-3">
              <div className="px-2 py-1 text-xs font-medium text-text-sidebar-dim uppercase tracking-wider">{g.label}</div>
              {g.items.map((c) => renderConvoItem(c))}
            </div>
          ))}

          {/* Project chats */}
          {projectChats.length > 0 && (
            <div className="mb-3 mt-2 pt-2 border-t border-border-dark">
              <div className="px-2 py-1 text-xs font-medium text-accent/70 uppercase tracking-wider flex items-center gap-1.5">
                <FolderOpen className="w-3 h-3" /> Projects
              </div>
              {projectChats.map((c) => renderConvoItem(c))}
            </div>
          )}

          {filtered.length === 0 && (
            <div className="px-3 py-8 text-center text-text-sidebar-dim text-sm">
              {search ? 'No matching conversations' : 'No conversations yet'}
            </div>
          )}
        </div>

        {/* Bottom nav */}
        <div className="border-t border-border-dark p-2 space-y-0.5">
          <button
            onClick={() => { navigate('/projects'); onClose(); }}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${location.pathname.startsWith('/projects') ? 'bg-sidebar-active text-text-sidebar' : 'text-text-sidebar-dim hover:bg-sidebar-hover hover:text-text-sidebar'}`}
          >
            <FolderOpen className="w-4 h-4" /> Projects
          </button>
          <button
            onClick={() => { navigate('/share'); onClose(); }}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${location.pathname === '/share' ? 'bg-sidebar-active text-text-sidebar' : 'text-text-sidebar-dim hover:bg-sidebar-hover hover:text-text-sidebar'}`}
          >
            <Send className="w-4 h-4" /> Share
          </button>
          <button
            onClick={() => { navigate('/gallery'); onClose(); }}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${location.pathname === '/gallery' ? 'bg-sidebar-active text-text-sidebar' : 'text-text-sidebar-dim hover:bg-sidebar-hover hover:text-text-sidebar'}`}
          >
            <Image className="w-4 h-4" /> Gallery
          </button>
          <button
            onClick={() => { navigate('/settings'); onClose(); }}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${location.pathname === '/settings' ? 'bg-sidebar-active text-text-sidebar' : 'text-text-sidebar-dim hover:bg-sidebar-hover hover:text-text-sidebar'}`}
          >
            <Settings className="w-4 h-4" /> Settings
          </button>

          {/* User */}
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-text-sidebar-dim hover:bg-sidebar-hover hover:text-text-sidebar transition text-sm"
            >
              <div className="w-6 h-6 rounded-full bg-accent/20 flex items-center justify-center text-accent text-xs font-medium">
                {user?.display_name?.[0]?.toUpperCase() || 'U'}
              </div>
              <span className="flex-1 text-left truncate">{user?.display_name || user?.username}</span>
              <ChevronDown className="w-3.5 h-3.5" />
            </button>
            {showUserMenu && (
              <div className="absolute bottom-full left-0 w-full mb-1 bg-sidebar-hover rounded-lg border border-border-dark overflow-hidden">
                <button
                  onClick={() => { logout(); navigate('/login'); }}
                  className="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-red-400 hover:bg-red-500/10 transition"
                >
                  <LogOut className="w-4 h-4" /> Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );

  function renderConvoItem(c: Conversation) {
    const isActive = c.id === activeConversationId;
    return (
      <div
        key={c.id}
        onClick={() => openConversation(c)}
        className={`group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer transition text-sm ${isActive ? 'bg-sidebar-active text-text-sidebar' : 'text-text-sidebar-dim hover:bg-sidebar-hover hover:text-text-sidebar'}`}
      >
        <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-60" />
        {editingId === c.id ? (
          <div className="flex-1 flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
            <input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && saveRename(c.id)}
              className="flex-1 bg-sidebar-bg text-text-sidebar text-sm px-1 py-0.5 rounded border border-border-dark focus:outline-none"
              autoFocus
            />
            <button onClick={() => saveRename(c.id)} className="p-0.5 hover:text-green-400"><Check className="w-3.5 h-3.5" /></button>
            <button onClick={() => setEditingId(null)} className="p-0.5 hover:text-red-400"><X className="w-3.5 h-3.5" /></button>
          </div>
        ) : (
          <>
            <span className="flex-1 truncate">{c.title}</span>
            <div className="hidden group-hover:flex items-center gap-0.5">
              <button onClick={(e) => toggleStar(c, e)} className={`p-0.5 transition ${c.is_starred ? 'text-yellow-400' : 'hover:text-yellow-400'}`}>
                <Star className="w-3.5 h-3.5" fill={c.is_starred ? 'currentColor' : 'none'} />
              </button>
              <button onClick={(e) => startRename(c, e)} className="p-0.5 hover:text-text-sidebar"><Pencil className="w-3.5 h-3.5" /></button>
              <button onClick={(e) => exportConversation(c.id, e)} className="p-0.5 hover:text-text-sidebar" title="Export"><Download className="w-3.5 h-3.5" /></button>
              <button onClick={(e) => deleteConversation(c.id, e)} className="p-0.5 hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
            </div>
          </>
        )}
      </div>
    );
  }
}
