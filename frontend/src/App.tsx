import React, { useState, useRef, useEffect, useMemo } from 'react';
import { 
  Send, 
  Terminal as TerminalIcon,
  Paperclip,
  Scroll,
  Sparkles,
  FileText,
  Layers,
  ChevronRight
} from 'lucide-react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import type { Message, ToolCall, ChatSession, ChatAttachment } from './types';
import { ChatMessage } from './components/ChatMessage';
import { Sidebar } from './components/Sidebar';
import { Settings } from './components/Settings';
import { v4 as uuidv4 } from 'uuid';

const modelOptions = [
  { value: 'openai/gpt-4o-mini', label: 'gpt-4o-mini' },
  { value: 'anthropic/claude-haiku-4.5', label: 'claude-haiku-4.5' },
  { value: 'google/gemini-2.5-flash', label: 'gemini-2.5-flash' },
];

// 动画关键帧样式
const animations = `
  @keyframes float {
    0% { transform: translateY(0px) rotate(0deg); }
    50% { transform: translateY(-20px) rotate(5deg); }
    100% { transform: translateY(0px) rotate(0deg); }
  }
  @keyframes blob-movement {
    0% { border-radius: 40% 60% 70% 30% / 40% 50% 60% 50%; }
    34% { border-radius: 70% 30% 50% 50% / 30% 30% 70% 70%; }
    67% { border-radius: 100% 60% 60% 100% / 100% 100% 60% 60%; }
    100% { border-radius: 40% 60% 70% 30% / 40% 50% 60% 50%; }
  }
  @keyframes leaf-fall {
    0% { transform: translate(0, -10%) rotate(0deg); opacity: 0; }
    10% { opacity: 0.8; }
    90% { opacity: 0.8; }
    100% { transform: translate(100px, 110vh) rotate(360deg); opacity: 0; }
  }
`;

interface Artifact {
  id: number;
  title: string;
  type: 'scroll' | 'code' | 'data';
  date: string;
  sessionId?: string;
}

function App() {
  const [userId, setUserId] = useState('');
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState('');
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [model, setModel] = useState(modelOptions[0].value);
  const [userPaths, setUserPaths] = useState<string[]>([]);
  const [pathError, setPathError] = useState('');
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [httpProxy, setHttpProxy] = useState('');
  const [httpsProxy, setHttpsProxy] = useState('');
  const [proxyError, setProxyError] = useState('');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [artifacts] = useState<Artifact[]>([
    { id: 1, title: '系统诊断报告 v1.0', type: 'scroll', date: new Date().toLocaleDateString('zh-CN') },
    { id: 2, title: '自动化脚本集合', type: 'code', date: new Date().toLocaleDateString('zh-CN') }
  ]);
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

  const fetchUserPaths = async (currentUserId: string) => {
    if (!currentUserId) return;
    try {
      const response = await fetch(
        `${apiUrl}/api/user/paths?user_id=${encodeURIComponent(currentUserId)}`
      );
      if (!response.ok) {
        throw new Error(`Load user paths failed: ${response.status}`);
      }
      const data = await response.json();
      setUserPaths(Array.isArray(data.paths) ? data.paths : []);
      setPathError('');
    } catch (err) {
      console.error('Failed to load user paths:', err);
      setPathError('加载路径配置失败');
    }
  };

  const saveUserPaths = async (paths: string[]) => {
    const currentUserId = userId || localStorage.getItem('mac_agent_user_id');
    if (!currentUserId) return;
    try {
      const response = await fetch(`${apiUrl}/api/user/paths`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: currentUserId,
          paths,
        }),
      });
      if (!response.ok) {
        throw new Error(`Save user paths failed: ${response.status}`);
      }
      const data = await response.json();
      setUserPaths(Array.isArray(data.paths) ? data.paths : []);
      setPathError('');
    } catch (err) {
      console.error('Failed to save user paths:', err);
      setPathError('保存路径配置失败');
    }
  };

  const fetchProxyConfig = async (currentUserId: string) => {
    if (!currentUserId) return;
    try {
      const response = await fetch(
        `${apiUrl}/api/user/proxy?user_id=${encodeURIComponent(currentUserId)}`
      );
      if (!response.ok) {
        throw new Error(`Load proxy config failed: ${response.status}`);
      }
      const data = await response.json();
      setHttpProxy(data.http_proxy || '');
      setHttpsProxy(data.https_proxy || '');
      setProxyError('');
    } catch (err) {
      console.error('Failed to load proxy config:', err);
      setProxyError('加载代理配置失败');
    }
  };

  const saveProxyConfig = async () => {
    const currentUserId = userId || localStorage.getItem('mac_agent_user_id');
    if (!currentUserId) return;
    try {
      const response = await fetch(`${apiUrl}/api/user/proxy`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: currentUserId,
          http_proxy: httpProxy.trim() || null,
          https_proxy: httpsProxy.trim() || null,
        }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Save proxy config failed: ${response.status}`);
      }
      const data = await response.json();
      setHttpProxy(data.http_proxy || '');
      setHttpsProxy(data.https_proxy || '');
      setProxyError('');
      alert('代理配置已保存');
    } catch (err) {
      console.error('Failed to save proxy config:', err);
      setProxyError(err instanceof Error ? err.message : '保存代理配置失败');
    }
  };

  useEffect(() => {
    initSessionState().catch((err) => {
      console.error('Failed to init session:', err);
    });
  }, []);

  useEffect(() => {
    if (userId) {
      fetchUserPaths(userId);
      fetchProxyConfig(userId);
    }
  }, [userId]);

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
    if (!input.trim() || isLoading || isUploading) return;
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
      blocks: [
        {
          type: 'content',
          content: input.trim(),
        },
      ],
    };

    const assistantMessageId = uuidv4();
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      toolCalls: [],
      blocks: [],
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
          attachments,
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
              const currentMsg = newMessages[msgIndex];
              const msg: Message = {
                ...currentMsg,
                toolCalls: [...(currentMsg.toolCalls || [])],
                blocks: [...(currentMsg.blocks || [])],
              };

              if (ev.event === 'content') {
                msg.content += data;
                const nextBlocks = msg.blocks || [];
                const lastBlock = nextBlocks[nextBlocks.length - 1];
                if (lastBlock?.type === 'content') {
                  lastBlock.content += data;
                } else {
                  nextBlocks.push({ type: 'content', content: data });
                }
                msg.blocks = nextBlocks;
              } else if (ev.event === 'tool_start') {
                const toolCall: ToolCall = {
                  id: data.tool_call_id,
                  name: data.name,
                  args: data.args,
                  status: 'running',
                };
                msg.toolCalls = [...(msg.toolCalls || []), toolCall];
                msg.blocks = [...(msg.blocks || []), { type: 'tool', toolCallId: toolCall.id }];
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
                const nextBlocks = msg.blocks || [];
                const lastBlock = nextBlocks[nextBlocks.length - 1];
                if (lastBlock?.type === 'content') {
                  lastBlock.content += `\n\n**Error:** ${data}`;
                } else {
                  nextBlocks.push({ type: 'content', content: `\n\n**Error:** ${data}` });
                }
                msg.blocks = nextBlocks;
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
              const currentMsg = newMessages[msgIndex];
              const msg: Message = {
                ...currentMsg,
                toolCalls: [...(currentMsg.toolCalls || [])],
                blocks: [...(currentMsg.blocks || [])],
              };
              msg.content += `\n\n**Parse Error:** ${ev.data}`;
              const nextBlocks = msg.blocks || [];
              const lastBlock = nextBlocks[nextBlocks.length - 1];
              if (lastBlock?.type === 'content') {
                lastBlock.content += `\n\n**Parse Error:** ${ev.data}`;
              } else {
                nextBlocks.push({ type: 'content', content: `\n\n**Parse Error:** ${ev.data}` });
              }
              msg.blocks = nextBlocks;
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
            const currentMsg = newMessages[msgIndex];
            const msg: Message = {
              ...currentMsg,
              toolCalls: [...(currentMsg.toolCalls || [])],
              blocks: [...(currentMsg.blocks || [])],
            };
            msg.content += `\n\n**Connection Error:** ${err instanceof Error ? err.message : String(err)}`;
            const nextBlocks = msg.blocks || [];
            const lastBlock = nextBlocks[nextBlocks.length - 1];
            if (lastBlock?.type === 'content') {
              lastBlock.content += `\n\n**Connection Error:** ${err instanceof Error ? err.message : String(err)}`;
            } else {
              nextBlocks.push({
                type: 'content',
                content: `\n\n**Connection Error:** ${err instanceof Error ? err.message : String(err)}`,
              });
            }
            msg.blocks = nextBlocks;
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
    } finally {
      setAttachments([]);
      setUploadError('');
    }
  };

  const uploadFile = async (file: File): Promise<ChatAttachment | null> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${apiUrl}/api/files`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.status}`);
    }
    const data = await response.json();
    return {
      file_id: data.id,
      filename: data.filename,
      content_type: data.content_type,
    };
  };

  const handleFilesSelected = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    setUploadError('');
    try {
      const results: ChatAttachment[] = [];
      for (const file of Array.from(files)) {
        const attachment = await uploadFile(file);
        if (attachment) results.push(attachment);
      }
      setAttachments((prev) => [...prev, ...results]);
    } catch (err) {
      console.error('Upload failed', err);
      setUploadError('文件上传失败');
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemoveAttachment = (fileId: string) => {
    setAttachments((prev) => prev.filter((item) => item.file_id !== fileId));
  };

  // 背景粒子
  const particles = Array.from({ length: 15 });

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#fdfbf7] font-serif text-[#4a3f35] relative">
      <style>{animations}</style>

      {/* 魔法动态背景 */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {/* 液态背景块 */}
        <div 
          className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[#f5e6d3] opacity-30 blur-[100px]" 
          style={{ animation: 'blob-movement 20s infinite alternate linear' }}
        />
        <div 
          className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[#e3f2fd] opacity-40 blur-[120px]" 
          style={{ animation: 'blob-movement 25s infinite alternate-reverse linear' }}
        />
        
        {/* 飘落的粒子 */}
        {particles.map((_, i) => (
          <div 
            key={i}
            className="absolute bg-white/60 rounded-full blur-[1px]"
            style={{
              left: `${Math.random() * 100}%`,
              width: `${Math.random() * 8 + 4}px`,
              height: `${Math.random() * 12 + 6}px`,
              top: '-5%',
              animation: `leaf-fall ${Math.random() * 10 + 10}s linear infinite`,
              animationDelay: `${Math.random() * 10}s`,
              opacity: 0.4
            }}
          />
        ))}
      </div>

      {/* 左侧边栏 - 仅显示历史记录 */}
      <Sidebar
        userId={userId}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onCreateSession={createSession}
        onLoadSession={loadSession}
        onSettingsClick={() => setIsSettingsOpen(true)}
      />

      {/* 中间：主聊天区域 */}
      <main className="flex-1 flex flex-col z-10 relative">
        {/* 顶部工具栏 */}
        <header className="h-16 flex items-center justify-between px-8 border-b border-[#e8dcc4] bg-white/10 backdrop-blur-md">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
            <span className="text-sm font-medium opacity-70">系统核心已就绪</span>
          </div>
        </header>

        {/* 消息展示区 */}
        <section className="flex-1 overflow-y-auto p-8 space-y-8 scroll-smooth">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center space-y-6">
              <div className="w-20 h-20 bg-gradient-to-br from-[#d4af37] to-[#aa8c2c] rounded-2xl flex items-center justify-center shadow-xl">
                <TerminalIcon className="w-10 h-10 text-white" />
              </div>
              <div className="text-center space-y-2">
                <p className="text-xl font-bold text-[#2c241d]">欢迎来到 MacAgent 智能工坊</p>
                <p className="text-sm text-[#a08b73]">今天想探索哪些系统魔法？</p>
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))
          )}
          <div ref={messagesEndRef} />
        </section>

        {/* 输入区域 */}
        <footer className="p-8 pt-0 bg-transparent">
          <form onSubmit={handleSubmit} className="max-w-4xl mx-auto space-y-4">
            {/* 附件上传 */}
            <div className="flex gap-3 items-center">
              <label className="text-[10px] font-bold uppercase tracking-wider text-[#a08b73]">
                附件
              </label>
              <div className="flex-1">
                <input
                  type="file"
                  multiple
                  onChange={(e) => handleFilesSelected(e.target.files)}
                  className="w-full text-[10px] text-[#4a3f35] file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-[10px] file:bg-[#f5efe1] file:text-[#4a3f35] hover:file:bg-[#eaddc0]"
                  disabled={isUploading}
                />
              </div>
            </div>

            {/* 附件显示 */}
            {attachments.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {attachments.map((item) => (
                  <span
                    key={item.file_id}
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#f5efe1] border border-[#e8dcc4] text-xs text-[#4a3f35]"
                  >
                    {item.filename || item.file_id}
                    <button
                      type="button"
                      onClick={() => handleRemoveAttachment(item.file_id)}
                      className="text-red-400 hover:text-red-600 text-[10px]"
                    >
                      移除
                    </button>
                  </span>
                ))}
              </div>
            )}
            {uploadError && <div className="text-xs text-red-600">{uploadError}</div>}

            {/* 主输入框 */}
            <div className="relative group">
              <div className="absolute -inset-1 bg-gradient-to-r from-[#d4af37]/20 via-[#e8dcc4]/20 to-[#d4af37]/20 rounded-[2rem] blur opacity-30 group-hover:opacity-60 transition duration-1000" />
              <div className="relative bg-white/70 backdrop-blur-2xl rounded-[1.8rem] border border-[#e8dcc4] shadow-2xl flex items-end p-2 pr-4 min-h-[64px] transition-all duration-300 focus-within:border-[#d4af37]/50 focus-within:shadow-[0_0_20px_rgba(212,175,55,0.15)]">
                <button 
                  type="button"
                  className="p-3 hover:bg-[#fdfbf7] rounded-full transition-colors group/upload relative"
                >
                  <Paperclip className="w-5 h-5 text-[#a08b73]" />
                  <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-[#4a3f35] text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover/upload:opacity-100 transition-opacity whitespace-nowrap">
                    上传附件
                  </div>
                </button>

                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="在此书写您的智慧..."
                  className="flex-1 bg-transparent border-none focus:ring-0 outline-none text-sm py-4 px-2 resize-none placeholder-[#a08b73]/50 text-[#4a3f35]"
                  disabled={isLoading || isUploading}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSubmit(e);
                    }
                  }}
                />

                <button
                  type="submit"
                  disabled={isLoading || isUploading || !input.trim()}
                  className={`p-3 rounded-2xl transition-all ${
                    input.trim() ? 'bg-[#d4af37] text-white shadow-lg hover:bg-[#aa8c2c]' : 'bg-gray-100 text-gray-300'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </form>
          <p className="text-center mt-4 text-[10px] opacity-40 uppercase tracking-widest text-[#a08b73]">
            AI 并非万能，请保持理性思考
          </p>
        </footer>
      </main>

      {/* 右侧：Artifact 成果展示 (真理印记) */}
      <aside className="w-80 flex flex-col z-10 border-l border-[#e8dcc4] bg-white/30 backdrop-blur-2xl">
        <div className="p-6">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-lg font-bold italic text-[#2c241d] flex items-center gap-2">
              <Scroll className="w-5 h-5 text-[#d4af37]" />
              真理印记
            </h2>
            <div className="flex gap-1">
              <div className="w-2 h-2 rounded-full bg-[#d4af37]/20"></div>
              <div className="w-2 h-2 rounded-full bg-[#d4af37]/40"></div>
              <div className="w-2 h-2 rounded-full bg-[#d4af37]/60"></div>
            </div>
          </div>

          <div className="space-y-4 max-h-[calc(100vh-400px)] overflow-y-auto">
            {artifacts.length === 0 ? (
              <div className="text-center py-8 text-[#a08b73] text-sm">
                暂无成果记录
              </div>
            ) : (
              artifacts.map((art) => (
                <div 
                  key={art.id} 
                  className="group relative bg-[#fdfbf7] p-4 rounded-2xl border border-[#e8dcc4] hover:border-[#d4af37] transition-all cursor-pointer overflow-hidden"
                  style={{ animation: 'float 6s infinite ease-in-out', animationDelay: `${art.id}s` }}
                >
                  {/* 装饰用的小背景图腾 */}
                  <div className="absolute -right-4 -bottom-4 opacity-[0.03] group-hover:opacity-[0.08] transition-opacity">
                    <Layers size={100} />
                  </div>

                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-white rounded-lg shadow-sm">
                      {art.type === 'scroll' ? (
                        <FileText className="w-4 h-4 text-[#d4af37]" />
                      ) : art.type === 'code' ? (
                        <TerminalIcon className="w-4 h-4 text-blue-400" />
                      ) : (
                        <Layers className="w-4 h-4 text-green-400" />
                      )}
                    </div>
                    <div className="flex-1">
                      <h3 className="text-sm font-bold opacity-80 group-hover:text-[#d4af37] transition-colors">
                        {art.title}
                      </h3>
                      <p className="text-[10px] opacity-40 mt-1 uppercase font-semibold">
                        {art.date}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 flex justify-between items-center">
                    <div className="flex -space-x-2">
                      {[1, 2, 3].map((i) => (
                        <div 
                          key={i} 
                          className="w-5 h-5 rounded-full border border-white bg-gray-200 overflow-hidden"
                        >
                          <div className="w-full h-full bg-gradient-to-br from-gray-100 to-gray-300"></div>
                        </div>
                      ))}
                    </div>
                    <button 
                      type="button"
                      className="text-[10px] font-bold text-[#d4af37] flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      查看详情 <ChevronRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="mt-12 p-6 rounded-3xl bg-gradient-to-br from-[#d4af37]/10 to-transparent border border-[#d4af37]/20">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-[#d4af37]" />
              <span className="text-xs font-bold uppercase tracking-wider">智力加成</span>
            </div>
            <p className="text-[11px] leading-relaxed opacity-60 italic text-[#4a3f35]">
              "在这个空间内，所有的中间产物都将被永恒记录。每一个咒语的改动都是通往伟大的阶梯。"
            </p>
          </div>
        </div>
      </aside>

      {/* 设置页面 */}
      <Settings
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        model={model}
        onModelChange={setModel}
        modelOptions={modelOptions}
        userPaths={userPaths}
        onPathsChange={async (paths) => {
          setUserPaths(paths);
          await saveUserPaths(paths);
        }}
        pathError={pathError}
        httpProxy={httpProxy}
        onHttpProxyChange={setHttpProxy}
        httpsProxy={httpsProxy}
        onHttpsProxyChange={setHttpsProxy}
        proxyError={proxyError}
        onSaveProxy={saveProxyConfig}
      />
    </div>
  );
}

export default App;
