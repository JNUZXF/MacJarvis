export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
  status: 'running' | 'completed' | 'failed';
}

export type MessageBlock =
  | {
      type: 'content';
      content: string;
    }
  | {
      type: 'tool';
      toolCallId: string;
    };

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
  blocks?: MessageBlock[];
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

export interface ChatAttachment {
  file_id: string;
  filename: string;
  content_type?: string | null;
}
