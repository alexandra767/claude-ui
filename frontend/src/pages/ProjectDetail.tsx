import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { projects as projectsApi } from '../api/client';
import { useChatStore } from '../stores/chatStore';
import {
  ArrowLeft, Settings, MessageSquare, Plus, Upload, FileText,
  Trash2, Save, Check, X
} from 'lucide-react';
import type { Project } from '../types';

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { setActiveConversation, setMessages } = useChatStore();
  const [project, setProject] = useState<Project | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editPrompt, setEditPrompt] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (projectId) loadProject();
  }, [projectId]);

  const loadProject = async () => {
    try {
      const data = await projectsApi.get(projectId!);
      setProject(data);
      setEditName(data.name);
      setEditDesc(data.description);
      setEditPrompt(data.system_prompt);
    } catch {
      navigate('/projects');
    }
  };

  const saveSettings = async () => {
    try {
      await projectsApi.update(projectId!, {
        name: editName,
        description: editDesc,
        system_prompt: editPrompt,
      });
      setProject((p) => p ? { ...p, name: editName, description: editDesc, system_prompt: editPrompt } : p);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {}
  };

  const deleteProject = async () => {
    if (!confirm('Delete this project? All project files will be removed.')) return;
    try {
      await projectsApi.delete(projectId!);
      navigate('/projects');
    } catch {}
  };

  const startChatInProject = () => {
    setActiveConversation(null);
    setMessages([]);
    navigate(`/chat?project=${projectId}`);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || !projectId) return;
    for (const file of Array.from(files)) {
      await projectsApi.uploadFile(projectId, file);
    }
    loadProject();
  };

  if (!project) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <div className="text-text-secondary">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-cream">
      {/* Header */}
      <div className="bg-white border-b border-border">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/projects')} className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cream transition">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-medium text-sm" style={{ backgroundColor: project.color }}>
                {project.name[0]?.toUpperCase()}
              </div>
              <div>
                <h1 className="text-lg font-semibold text-text-primary">{project.name}</h1>
                {project.description && <p className="text-xs text-text-secondary">{project.description}</p>}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className={`p-2 rounded-lg transition ${showSettings ? 'bg-cream text-accent' : 'text-text-secondary hover:text-text-primary hover:bg-cream'}`}
            >
              <Settings className="w-5 h-5" />
            </button>
            <button
              onClick={startChatInProject}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent text-white text-sm font-medium hover:bg-accent-hover transition"
            >
              <Plus className="w-4 h-4" /> New Chat
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8">
        {showSettings ? (
          /* Settings view */
          <div className="bg-white rounded-2xl border border-border p-6 space-y-6">
            <h2 className="text-lg font-semibold text-text-primary">Project Settings</h2>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-1.5">Name</label>
              <input value={editName} onChange={(e) => setEditName(e.target.value)} className="w-full max-w-md px-4 py-2.5 rounded-xl border border-border bg-cream focus:outline-none focus:ring-2 focus:ring-accent/30 text-text-primary" />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-1.5">Description</label>
              <textarea value={editDesc} onChange={(e) => setEditDesc(e.target.value)} rows={2} className="w-full max-w-md px-4 py-2.5 rounded-xl border border-border bg-cream focus:outline-none focus:ring-2 focus:ring-accent/30 text-text-primary resize-none" />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-1.5">Custom Instructions</label>
              <p className="text-xs text-text-secondary mb-2">These instructions will be included in every conversation in this project.</p>
              <textarea
                value={editPrompt}
                onChange={(e) => setEditPrompt(e.target.value)}
                rows={6}
                className="w-full px-4 py-3 rounded-xl border border-border bg-cream focus:outline-none focus:ring-2 focus:ring-accent/30 text-text-primary resize-none font-mono text-sm"
                placeholder="e.g., You are a helpful coding assistant specialized in React and TypeScript..."
              />
            </div>

            {/* Files */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <label className="text-sm font-medium text-text-primary">Project Files</label>
                <label className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-accent hover:bg-accent/5 cursor-pointer transition">
                  <Upload className="w-3.5 h-3.5" /> Upload
                  <input type="file" multiple onChange={handleFileUpload} className="hidden" />
                </label>
              </div>
              {project.files && project.files.length > 0 ? (
                <div className="space-y-2">
                  {project.files.map((f) => (
                    <div key={f.id} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-cream text-sm">
                      <FileText className="w-4 h-4 text-text-secondary" />
                      <span className="text-text-primary">{f.filename}</span>
                      <span className="text-xs text-text-secondary">{(f.file_size / 1024).toFixed(1)} KB</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-text-secondary">No files uploaded yet.</p>
              )}
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button onClick={saveSettings} className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent text-white font-medium hover:bg-accent-hover transition">
                {saved ? <><Check className="w-4 h-4" /> Saved</> : <><Save className="w-4 h-4" /> Save</>}
              </button>
              <button onClick={deleteProject} className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-red-200 text-red-600 text-sm font-medium hover:bg-red-50 transition">
                <Trash2 className="w-4 h-4" /> Delete Project
              </button>
            </div>
          </div>
        ) : (
          /* Conversations view */
          <div>
            {project.conversations && project.conversations.length > 0 ? (
              <div className="space-y-2">
                {project.conversations.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => navigate(`/chat/${c.id}`)}
                    className="w-full flex items-center gap-3 bg-white rounded-xl border border-border p-4 hover:shadow-sm hover:border-accent/30 transition text-left"
                  >
                    <MessageSquare className="w-5 h-5 text-text-secondary shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-text-primary truncate">{c.title}</div>
                      <div className="text-xs text-text-secondary">{new Date(c.updated_at).toLocaleDateString()}</div>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="text-center py-16">
                <MessageSquare className="w-12 h-12 text-text-secondary/30 mx-auto mb-4" />
                <h3 className="text-text-primary font-medium mb-1">No conversations yet</h3>
                <p className="text-sm text-text-secondary mb-4">Start a new chat to begin.</p>
                <button onClick={startChatInProject} className="px-5 py-2.5 rounded-xl bg-accent text-white font-medium hover:bg-accent-hover transition">
                  Start Chat
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
