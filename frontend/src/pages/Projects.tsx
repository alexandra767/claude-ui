import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { projects as projectsApi } from '../api/client';
import {
  ArrowLeft, Plus, FolderOpen, MessageSquare, X
} from 'lucide-react';
import type { Project } from '../types';

const COLORS = ['#DA7756', '#5B8DEF', '#43A887', '#C75BAA', '#E6A23C', '#7C5CFC'];

export default function Projects() {
  const navigate = useNavigate();
  const [projectList, setProjectList] = useState<Project[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [color, setColor] = useState(COLORS[0]);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await projectsApi.list();
      setProjectList(data);
    } catch {}
  };

  const createProject = async () => {
    if (!name.trim()) return;
    try {
      const project = await projectsApi.create({ name: name.trim(), description, color });
      setProjectList((prev) => [project, ...prev]);
      setShowCreate(false);
      setName('');
      setDescription('');
      navigate(`/projects/${project.id}`);
    } catch {}
  };

  return (
    <div className="min-h-screen bg-cream">
      {/* Header */}
      <div className="bg-white border-b border-border">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/')} className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cream transition">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-lg font-semibold text-text-primary">Projects</h1>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent text-white text-sm font-medium hover:bg-accent-hover transition"
          >
            <Plus className="w-4 h-4" /> New Project
          </button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Project grid */}
        {projectList.length === 0 ? (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-accent/10 mb-4">
              <FolderOpen className="w-8 h-8 text-accent" />
            </div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">No projects yet</h2>
            <p className="text-text-secondary text-sm mb-6">
              Projects let you organize conversations with custom instructions.
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className="px-5 py-2.5 rounded-xl bg-accent text-white font-medium hover:bg-accent-hover transition"
            >
              Create your first project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projectList.map((p) => (
              <button
                key={p.id}
                onClick={() => navigate(`/projects/${p.id}`)}
                className="text-left bg-white rounded-2xl border border-border p-5 hover:shadow-md hover:border-accent/30 transition group"
              >
                <div className="flex items-start gap-3 mb-3">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-medium shrink-0"
                    style={{ backgroundColor: p.color }}
                  >
                    {p.name[0]?.toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="font-medium text-text-primary truncate">{p.name}</div>
                    <div className="text-sm text-text-secondary truncate">{p.description || 'No description'}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-text-secondary">
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>{p.conversation_count || 0} conversations</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center px-4">
          <div className="bg-white rounded-2xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-text-primary">New Project</h2>
              <button onClick={() => setShowCreate(false)} className="p-1.5 rounded-lg text-text-secondary hover:bg-cream transition">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">Name</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-border bg-cream focus:outline-none focus:ring-2 focus:ring-accent/30 text-text-primary"
                  placeholder="My project"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  className="w-full px-4 py-2.5 rounded-xl border border-border bg-cream focus:outline-none focus:ring-2 focus:ring-accent/30 text-text-primary resize-none"
                  placeholder="What's this project about?"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">Color</label>
                <div className="flex gap-2">
                  {COLORS.map((c) => (
                    <button
                      key={c}
                      onClick={() => setColor(c)}
                      className={`w-8 h-8 rounded-full transition ${color === c ? 'ring-2 ring-offset-2 ring-accent' : ''}`}
                      style={{ backgroundColor: c }}
                    />
                  ))}
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button onClick={() => setShowCreate(false)} className="flex-1 px-4 py-2.5 rounded-xl border border-border text-text-secondary font-medium hover:bg-cream transition">
                  Cancel
                </button>
                <button onClick={createProject} disabled={!name.trim()} className="flex-1 px-4 py-2.5 rounded-xl bg-accent text-white font-medium hover:bg-accent-hover transition disabled:opacity-50">
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
