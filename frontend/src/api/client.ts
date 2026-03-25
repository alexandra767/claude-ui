const API_BASE = '/api';

function getHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const token = localStorage.getItem('token');
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

function authHeader(): Record<string, string> {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...getHeaders(), ...options?.headers },
  });
  if (res.status === 401) {
    // Only redirect if we're not already on the login page
    if (!window.location.pathname.startsWith('/login')) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

// Auth
export const auth = {
  signup: (data: { email: string; username: string; password: string; display_name?: string }) =>
    request<{ token: string; user: any }>('/auth/signup', { method: 'POST', body: JSON.stringify(data) }),
  login: (data: { email: string; password: string }) =>
    request<{ token: string; user: any }>('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  me: () => request<any>('/auth/me'),
  updateProfile: (data: { display_name?: string; theme?: string; custom_instructions?: string }) =>
    request<any>('/auth/me', { method: 'PUT', body: JSON.stringify(data) }),
};

// Chat
export const chat = {
  listConversations: () => request<any[]>('/chat/conversations'),
  getConversation: (id: string) => request<any>(`/chat/conversations/${id}`),
  updateConversation: (id: string, data: { title?: string; is_starred?: boolean; project_id?: string }) =>
    request<any>(`/chat/conversations/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteConversation: (id: string) =>
    request<any>(`/chat/conversations/${id}`, { method: 'DELETE' }),
  sendMessage: (data: {
    conversation_id?: string;
    message: string;
    model?: string;
    project_id?: string;
    persona?: string;
    attachments?: any[];
  }) => {
    return fetch(`${API_BASE}/chat/send`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
  },
  getModels: () => request<{ models: string[] }>('/chat/models'),
};

// Projects
export const projects = {
  list: () => request<any[]>('/projects/'),
  create: (data: { name: string; description?: string; system_prompt?: string; color?: string }) =>
    request<any>('/projects/', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => request<any>(`/projects/${id}`),
  update: (id: string, data: { name?: string; description?: string; system_prompt?: string; color?: string }) =>
    request<any>(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string) => request<any>(`/projects/${id}`, { method: 'DELETE' }),
  uploadFile: async (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/projects/${projectId}/files`, {
      method: 'POST',
      headers: authHeader(),
      body: formData,
    });
    return res.json();
  },
};

// Files
export const files = {
  upload: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/files/upload`, {
      method: 'POST',
      headers: authHeader(),
      body: formData,
    });
    return res.json();
  },
  read: (filename: string) => request<{ filename: string; content: string }>(`/files/read/${filename}`),
};

// Tools
export const tools = {
  list: () => request<{ tools: any[] }>('/tools/available'),
  executeCode: (code: string, language = 'python') =>
    request<{ stdout: string; stderr: string; returncode: number }>('/tools/execute', {
      method: 'POST',
      body: JSON.stringify({ code, language }),
    }),
  webSearch: (query: string) =>
    request<{ results: any[] }>('/tools/search', {
      method: 'POST',
      body: JSON.stringify({ query }),
    }),
};
