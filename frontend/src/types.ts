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

export interface TTSConfig {
  enabled: boolean;
  voice: string;
  model: string;
  minSegmentLength: number;
  maxSegmentLength: number;
  preferSegmentLength: number;
}

export interface TTSVoice {
  id: string;
  name: string;
  language: string;
  gender: 'male' | 'female';
  models?: string[]; // 该音色支持的模型列表
}

export interface TTSModel {
  id: string;
  name: string;
  description: string;
}

export interface WakeWordConfig {
  enabled: boolean;
  keywords: string[];
  commandTimeoutMs: number;
  cooldownMs: number;
  bargeIn: boolean;
  stripWakeWord: boolean;
}
