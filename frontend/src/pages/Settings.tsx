import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useChatStore } from '../stores/chatStore';
import { auth } from '../api/client';
import { applyTheme } from '../hooks/useTheme';
import {
  ArrowLeft, User, Palette, Shield, Database, Bell,
  Monitor, Sun, Moon, Save, Check, Trash2
} from 'lucide-react';

type Tab = 'profile' | 'appearance' | 'data' | 'security';

export default function Settings() {
  const navigate = useNavigate();
  const { user, updateUser, logout } = useAuthStore();
  const { selectedModel, setSelectedModel, conversations } = useChatStore();
  const [activeTab, setActiveTab] = useState<Tab>('profile');
  const [displayName, setDisplayName] = useState(user?.display_name || '');
  const [theme, setTheme] = useState(user?.theme || 'system');
  const [customInstructions, setCustomInstructions] = useState(user?.custom_instructions || '');
  const [saved, setSaved] = useState(false);
  const [models, setModels] = useState<string[]>([]);

  const tabs: { id: Tab; label: string; icon: typeof User }[] = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'data', label: 'Data & Storage', icon: Database },
    { id: 'security', label: 'Security', icon: Shield },
  ];

  const saveProfile = async () => {
    try {
      await auth.updateProfile({ display_name: displayName, theme, custom_instructions: customInstructions });
      updateUser({ display_name: displayName, theme });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {}
  };

  const loadModels = async () => {
    if (models.length > 0) return;
    try {
      const { chat: chatApi } = await import('../api/client');
      const data = await chatApi.getModels();
      setModels(data.models);
    } catch {}
  };

  return (
    <div className="min-h-screen bg-cream">
      {/* Header */}
      <div className="bg-white border-b border-border">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/')} className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cream transition">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-lg font-semibold text-text-primary">Settings</h1>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8 flex gap-8">
        {/* Tabs */}
        <div className="w-48 shrink-0 space-y-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => { setActiveTab(tab.id); if (tab.id === 'appearance') loadModels(); }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition ${
                  activeTab === tab.id
                    ? 'bg-white shadow-sm text-text-primary font-medium'
                    : 'text-text-secondary hover:text-text-primary hover:bg-white/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div className="flex-1 bg-white rounded-2xl border border-border p-8">
          {activeTab === 'profile' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-text-primary mb-1">Profile</h2>
                <p className="text-sm text-text-secondary">Manage your account information</p>
              </div>

              <div className="flex items-center gap-4">
                <label className="relative cursor-pointer group">
                  {user?.avatar_url ? (
                    <img src={user.avatar_url} alt="Avatar" className="w-16 h-16 rounded-full object-cover" />
                  ) : (
                    <div className="w-16 h-16 rounded-full bg-accent/15 flex items-center justify-center text-accent text-2xl font-medium">
                      {displayName?.[0]?.toUpperCase() || 'U'}
                    </div>
                  )}
                  <div className="absolute inset-0 rounded-full bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition">
                    <span className="text-white text-xs font-medium">Change</span>
                  </div>
                  <input type="file" accept="image/*" className="hidden" onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    const formData = new FormData();
                    formData.append('file', file);
                    const token = localStorage.getItem('token');
                    const res = await fetch('/api/auth/avatar', {
                      method: 'POST',
                      headers: token ? { Authorization: `Bearer ${token}` } : {},
                      body: formData,
                    });
                    if (res.ok) {
                      const data = await res.json();
                      updateUser({ avatar_url: data.avatar_url });
                    }
                  }} />
                </label>
                <div>
                  <div className="text-text-primary font-medium">{user?.username}</div>
                  <div className="text-sm text-text-secondary">{user?.email}</div>
                  <div className="text-xs text-text-secondary mt-0.5">Click photo to change</div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">Display Name</label>
                <input
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full max-w-md px-4 py-2.5 rounded-xl border border-border bg-cream focus:outline-none focus:ring-2 focus:ring-accent/30 text-text-primary"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">Custom Instructions</label>
                <p className="text-xs text-text-secondary mb-2">Tell the AI about yourself and how you want it to respond. These apply to all conversations.</p>
                <textarea
                  value={customInstructions}
                  onChange={(e) => setCustomInstructions(e.target.value)}
                  rows={5}
                  className="w-full px-4 py-3 rounded-xl border border-border bg-cream focus:outline-none focus:ring-2 focus:ring-accent/30 text-text-primary resize-none text-sm"
                  placeholder="e.g., I'm a software developer. I prefer concise answers with code examples. Use Python unless I specify otherwise."
                />
              </div>

              <button
                onClick={saveProfile}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent text-white font-medium hover:bg-accent-hover transition"
              >
                {saved ? <><Check className="w-4 h-4" /> Saved</> : <><Save className="w-4 h-4" /> Save Changes</>}
              </button>
            </div>
          )}

          {activeTab === 'appearance' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-text-primary mb-1">Appearance</h2>
                <p className="text-sm text-text-secondary">Customize how the app looks</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-3">Theme</label>
                <div className="flex gap-3">
                  {[
                    { id: 'light', label: 'Light', icon: Sun },
                    { id: 'dark', label: 'Dark', icon: Moon },
                    { id: 'system', label: 'System', icon: Monitor },
                  ].map(({ id, label, icon: Icon }) => (
                    <button
                      key={id}
                      onClick={() => { setTheme(id); applyTheme(id); }}
                      className={`flex items-center gap-2 px-4 py-3 rounded-xl border-2 transition cursor-pointer ${
                        theme === id ? 'border-accent bg-accent/15 text-accent font-semibold' : 'border-border bg-cream text-text-primary hover:border-accent/40'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      <span className="text-sm font-medium">{label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-3">Default Model</label>
                <div className="space-y-2 max-w-md">
                  {(models.length > 0 ? models : [selectedModel]).map((m) => (
                    <button
                      key={m}
                      onClick={() => setSelectedModel(m)}
                      className={`w-full text-left px-4 py-3 rounded-xl border transition ${
                        m === selectedModel ? 'border-accent bg-accent/5 text-accent font-medium' : 'border-border text-text-primary hover:border-accent/30'
                      }`}
                    >
                      {m}
                    </button>
                  ))}
                </div>
              </div>

              <button onClick={saveProfile} className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent text-white font-medium hover:bg-accent-hover transition">
                {saved ? <><Check className="w-4 h-4" /> Saved</> : <><Save className="w-4 h-4" /> Save Changes</>}
              </button>
            </div>
          )}

          {activeTab === 'data' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-text-primary mb-1">Data & Storage</h2>
                <p className="text-sm text-text-secondary">Manage your conversation data</p>
              </div>

              <div className="bg-cream rounded-xl p-4 space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">Total conversations</span>
                  <span className="text-text-primary font-medium">{conversations.length}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">Storage</span>
                  <span className="text-text-primary font-medium">Local (SQLite)</span>
                </div>
              </div>

              <div className="border-t border-border pt-6">
                <h3 className="text-sm font-medium text-red-600 mb-2">Danger Zone</h3>
                <p className="text-sm text-text-secondary mb-4">These actions cannot be undone.</p>
                <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-red-200 text-red-600 text-sm font-medium hover:bg-red-50 transition">
                  <Trash2 className="w-4 h-4" /> Delete All Conversations
                </button>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-text-primary mb-1">Security</h2>
                <p className="text-sm text-text-secondary">Manage your account security</p>
              </div>

              <div className="bg-cream rounded-xl p-4 space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">Authentication</span>
                  <span className="text-green-600 font-medium">Active</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">Session</span>
                  <span className="text-text-primary font-medium">JWT (30 days)</span>
                </div>
              </div>

              <div className="border-t border-border pt-6">
                <button
                  onClick={() => { logout(); navigate('/login'); }}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-red-200 text-red-600 text-sm font-medium hover:bg-red-50 transition"
                >
                  Sign out of all devices
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
