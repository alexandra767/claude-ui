import { create } from 'zustand';
import type { Conversation, Message, Artifact } from '../types';

interface UserLocation {
  lat: number;
  lon: number;
  city?: string;
}

interface ChatState {
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  selectedModel: string;
  activeArtifact: Artifact | null;
  showArtifactPanel: boolean;
  userLocation: UserLocation | null;

  setConversations: (convos: Conversation[]) => void;
  setActiveConversation: (id: string | null) => void;
  setMessages: (msgs: Message[]) => void;
  addMessage: (msg: Message) => void;
  setStreaming: (v: boolean) => void;
  appendStreamContent: (chunk: string) => void;
  resetStreamContent: () => void;
  setSelectedModel: (model: string) => void;
  setActiveArtifact: (artifact: Artifact | null) => void;
  setShowArtifactPanel: (v: boolean) => void;
  removeConversation: (id: string) => void;
  updateConversation: (id: string, updates: Partial<Conversation>) => void;
  setUserLocation: (loc: UserLocation) => void;
  detectLocation: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  conversations: [],
  activeConversationId: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',
  selectedModel: 'qwen3.5:122b',
  activeArtifact: null,
  showArtifactPanel: false,
  userLocation: null,

  setConversations: (conversations) => set({ conversations }),
  setActiveConversation: (id) => set({ activeConversationId: id }),
  setMessages: (messages) => set({ messages }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setStreaming: (isStreaming) => set({ isStreaming }),
  appendStreamContent: (chunk) => set((s) => ({ streamingContent: s.streamingContent + chunk })),
  resetStreamContent: () => set({ streamingContent: '' }),
  setSelectedModel: (selectedModel) => set({ selectedModel }),
  setActiveArtifact: (activeArtifact) => set({ activeArtifact, showArtifactPanel: !!activeArtifact }),
  setShowArtifactPanel: (showArtifactPanel) => set({ showArtifactPanel }),
  removeConversation: (id) => set((s) => ({
    conversations: s.conversations.filter((c) => c.id !== id),
    activeConversationId: s.activeConversationId === id ? null : s.activeConversationId,
    messages: s.activeConversationId === id ? [] : s.messages,
  })),
  updateConversation: (id, updates) => set((s) => ({
    conversations: s.conversations.map((c) => c.id === id ? { ...c, ...updates } : c),
  })),
  setUserLocation: (userLocation) => set({ userLocation }),
  detectLocation: () => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          set({
            userLocation: {
              lat: position.coords.latitude,
              lon: position.coords.longitude,
            },
          });
          // Send to backend for reverse geocoding
          fetch(`/api/location/update`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${localStorage.getItem('token')}`,
            },
            body: JSON.stringify({
              lat: position.coords.latitude,
              lon: position.coords.longitude,
            }),
          }).catch(() => {});
        },
        () => {
          // Geolocation denied — backend falls back to IP
        },
        { timeout: 5000, maximumAge: 600000 }
      );
    }
  },
}));
