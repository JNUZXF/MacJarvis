import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Send, Terminal as TerminalIcon } from 'lucide-react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import type { Message, ToolCall, ChatSession } from './types';
import { ChatMessage } from './components/ChatMessage';
import { v4 as uuidv4 } from 'uuid';

const modelOptions = [
  { value: 'openai/gpt-4o-mini', label: 'gpt-4o-mini' },
  { value: 'anthropic/claude-haiku-4.5', label: 'claude-haiku-4.5' },
  { value: 'google/gemini-2.5-flash', label: 'gemini-2.5-flash' },
];

function App() {
  const [userId, setUserId] = useState('');
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState('');
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [model, setModel] = useState(modelOptions[0].value);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const apiUrl = import.meta.env.VITE_API_URL || '';

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId),
    [sessions, activeSessionId]
  );

  const messages = activeSession?.messages ?? [];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const initSessionState = async () => {
    const storedUserId = localStorage.getItem('mac_agent_user_id');
    const storedActive = localStorage.getItem('mac_agent_active_session');
    const response = await fetch(`${apiUrl}/api/session/init`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: storedUserId || undefined,
        active_session_id: storedActive || undefined,
      }),
    });
    if (!response.ok) {
      throw new Error(`Init session failed: ${response.status}`);
    }
    const data = await response.json();
    setUserId(data.user_id);
    localStorage.setItem('mac_agent_user_id', data.user_id);
    setSessions(Array.isArray(data.sessions) ? data.sessions : []);
    const nextActive = data.active_session_id || data.sessions?.[0]?.id || '';
    setActiveSessionId(nextActive);
    if (nextActive) {
      localStorage.setItem('mac_agent_active_session', nextActive);
    }
    return {
      userId: data.user_id,
      activeSessionId: nextActive,
      sessions: Array.isArray(data.sessions) ? data.sessions : [],
    };
  };

  useEffect(() => {
    initSessionState().catch((err) => {
      console.error('Failed to init session:', err);
    });
  }, []);

  useEffect(() => {
    if (activeSessionId) {
      localStorage.setItem('mac_agent_active_session', activeSessionId);
    }
  }, [activeSessionId]);

  const createSessionTitle = (content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return '新会话';
    return trimmed.length > 24 ? `${trimmed.slice(0, 24)}...` : trimmed;
  };

  const createSession = async (title = '新会话') => {
    const currentUserId = userId || localStorage.getItem('mac_agent_user_id');
    if (!currentUserId) {
      const initState = await initSessionState();
      if (!initState.userId) {
        return '';
      }
    }
    const response = await fetch(`${apiUrl}/api/session/new`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: currentUserId || localStorage.getItem('mac_agent_user_id'),
        title,
      }),
    });
    if (!response.ok) {
      console.error('Failed to create session:', response.status);
      return '';
    }
    const session: ChatSession = await response.json();
    setSessions((prev) => [session, ...prev]);
    setActiveSessionId(session.id);
    localStorage.setItem('mac_agent_active_session', session.id);
    return session.id;
  };

  const loadSession = async (sessionId: string) => {
    const currentUserId = userId || localStorage.getItem('mac_agent_user_id');
    if (!currentUserId) {
      return;
    }
    const response = await fetch(
      `${apiUrl}/api/session/${sessionId}?user_id=${encodeURIComponent(currentUserId)}`
    );
    if (!response.ok) {
      console.error('Failed to load session:', response.status);
      return;
    }
    const session: ChatSession = await response.json();
    setSessions((prev) => prev.map((item) => (item.id === sessionId ? session : item)));
    setActiveSessionId(sessionId);
    localStorage.setItem('mac_agent_active_session', sessionId);
  };

  const updateSessionMessages = (sessionId: string, updater: (messages: Message[]) => Message[]) => {
    setSessions((prev) =>
      prev.map((session) => {
        if (session.id !== sessionId) return session;
        const nextMessages = updater(session.messages);
        const shouldUpdateTitle = session.title === '新会话' && session.messages.length === 0;
        return {
          ...session,
          messages: nextMessages,
          title: shouldUpdateTitle ? createSessionTitle(nextMessages[0]?.content ?? '') : session.title,
          updatedAt: Date.now(),
        };
      })
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    let currentUserId = userId;
    if (!currentUserId) {
      const initState = await initSessionState();
      currentUserId = initState.userId;
    }
    let sessionId = activeSessionId;
    if (!sessionId) {
      sessionId = await createSession();
    }
    if (!sessionId || !currentUserId) {
      console.error('Missing user_id or session_id');
      return;
    }

    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: input.trim(),
    };

    const assistantMessageId = uuidv4();
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      toolCalls: [],
    };

    updateSessionMessages(sessionId, (prev) => [...prev, userMessage, assistantMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // 使用相对路径，由 nginx 代理到后端
      await fetchEventSource(`${apiUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          model,
          user_id: currentUserId,
          session_id: sessionId,
        }),
        onmessage(ev) {
          try {
            // 忽略空事件（如 SSE 注释/心跳）
            if (!ev.data || ev.data.trim() === '') {
              return;
            }
            const data = JSON.parse(ev.data);
            
            updateSessionMessages(sessionId, (prevMessages) => {
              const newMessages = [...prevMessages];
              const msgIndex = newMessages.findIndex(m => m.id === assistantMessageId);
              if (msgIndex === -1) return prevMessages;
              const msg = { ...newMessages[msgIndex] };

              if (ev.event === 'content') {
                msg.content += data;
              } else if (ev.event === 'tool_start') {
                const toolCall: ToolCall = {
                  id: data.tool_call_id,
                  name: data.name,
                  args: data.args,
                  status: 'running',
                };
                msg.toolCalls = [...(msg.toolCalls || []), toolCall];
              } else if (ev.event === 'tool_result') {
                if (msg.toolCalls) {
                  msg.toolCalls = msg.toolCalls.map(tc =>
                    tc.id === data.tool_call_id
                      ? {
                          ...tc,
                          result: data.result,
                          status: data.result?.ok === false ? 'failed' : 'completed',
                        }
                      : tc
                  );
                }
              } else if (ev.event === 'error') {
                msg.content += `\n\n**Error:** ${data}`;
                setIsLoading(false);
              }

              newMessages[msgIndex] = msg;
              return newMessages;
            });
          } catch (parseErr) {
            console.error('Failed to parse SSE data:', parseErr, ev);
            // 如果解析失败，尝试直接显示原始数据
            updateSessionMessages(sessionId, (prevMessages) => {
              const newMessages = [...prevMessages];
              const msgIndex = newMessages.findIndex(m => m.id === assistantMessageId);
              if (msgIndex === -1) return prevMessages;
              const msg = { ...newMessages[msgIndex] };
              msg.content += `\n\n**Parse Error:** ${ev.data}`;
              newMessages[msgIndex] = msg;
              return newMessages;
            });
          }
        },
        onerror(err) {
          console.error('EventSource failed:', err);
          updateSessionMessages(sessionId, (prevMessages) => {
            const newMessages = [...prevMessages];
            const msgIndex = newMessages.findIndex(m => m.id === assistantMessageId);
            if (msgIndex === -1) return prevMessages;
            const msg = { ...newMessages[msgIndex] };
            msg.content += `\n\n**Connection Error:** ${err instanceof Error ? err.message : String(err)}`;
            newMessages[msgIndex] = msg;
            return newMessages;
          });
          setIsLoading(false);
          // 不抛出错误，让连接正常关闭
        },
        onclose() {
          setIsLoading(false);
        }
      });
    } catch (err) {
      console.error('Request failed', err);
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-100 font-sans">
      <div className="hidden md:flex flex-col w-64 bg-gray-900 text-white p-4">
        <div className="flex items-center gap-2 mb-8 px-2">
          <TerminalIcon className="w-6 h-6 text-blue-400" />
          <h1 className="text-xl font-bold tracking-tight">MacAgent</h1>
        </div>

        <div className="mb-6 px-2">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">User</div>
          <div className="text-xs text-gray-300 break-all">{userId || '生成中...'}</div>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          <div className="flex items-center justify-between text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 px-2">
            <span>Sessions</span>
            <button
              type="button"
              onClick={() => createSession()}
              className="text-blue-300 hover:text-blue-200"
            >
              新建
            </button>
          </div>
          <ul className="space-y-1 text-sm text-gray-300">
            {sessions.length === 0 ? (
              <li className="px-2 py-1.5 text-gray-500">暂无会话</li>
            ) : (
              sessions.map((session) => (
                <li
                  key={session.id}
                  className={`px-2 py-1.5 rounded cursor-pointer ${
                    session.id === activeSessionId ? 'bg-gray-800 text-white' : 'hover:bg-gray-800'
                  }`}
                  onClick={() => loadSession(session.id)}
                >
                  {session.title || '新会话'}
                </li>
              ))
            )}
          </ul>
        </div>

        <div className="mt-auto pt-4 border-t border-gray-800 text-xs text-gray-500">
          Powered by Trae & OpenAI
        </div>
      </div>

      <div className="flex-1 flex flex-col max-w-5xl mx-auto w-full bg-white shadow-xl">
        <header className="md:hidden h-14 bg-gray-900 text-white flex items-center px-4">
          <TerminalIcon className="w-5 h-5 mr-2 text-blue-400" />
          <span className="font-bold">MacAgent</span>
        </header>

        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-4">
              <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center">
                <TerminalIcon className="w-8 h-8 text-gray-400" />
              </div>
              <p className="text-lg font-medium">How can I help you manage your Mac today?</p>
            </div>
          ) : (
            messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <form onSubmit={handleSubmit} className="relative max-w-4xl mx-auto space-y-3">
            <div className="flex items-center gap-3">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Base Model
              </label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition-all bg-white"
                disabled={isLoading}
              >
                {modelOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Check system load, find large files, or restart a service..."
                className="w-full pl-4 pr-12 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition-all shadow-sm"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="absolute right-2 top-2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </form>
          <div className="text-center text-xs text-gray-400 mt-2">
            AI can make mistakes. Please verify important commands.
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
