export interface User {
  id: string;
  email: string;
  username: string;
  display_name: string;
  avatar_url: string;
  theme: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  model: string;
  project_id: string | null;
  is_starred: boolean;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  model?: string;
  artifacts?: Artifact[];
  attachments?: Attachment[];
  images?: { filename: string; prompt: string }[];
  thinking?: string;
  tool_calls?: ToolCall[];
  tool_results?: ToolResult[];
  token_count?: number;
  created_at: string;
}

export interface Artifact {
  id: string;
  type: 'code' | 'document' | 'html' | 'svg' | 'react' | 'mermaid';
  title: string;
  content: string;
  language?: string;
}

export interface Attachment {
  filename: string;
  path: string;
  type: string;
  size: number;
}

export interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
}

export interface ToolResult {
  name: string;
  result: unknown;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  color: string;
  created_at: string;
  updated_at: string;
  conversations?: { id: string; title: string; updated_at: string }[];
  files?: { id: string; filename: string; file_type: string; file_size: number }[];
  conversation_count?: number;
}

export interface ToolInfo {
  name: string;
  description: string;
  icon: string;
}
