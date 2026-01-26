export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
  status: 'running' | 'completed' | 'failed';
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  input: string;
}

export interface UserPathsResponse {
  user_id: string;
  paths: string[];
}
