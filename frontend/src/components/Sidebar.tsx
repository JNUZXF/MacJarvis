// 左侧边栏组件
// 路径: frontend/src/components/Sidebar.tsx
// 功能: 显示用户信息、新建会话按钮、历史聊天记录、设置入口

import React from 'react';
import { Plus, MessageSquare, BookOpen, Settings } from 'lucide-react';
import type { ChatSession } from '../types';

interface SidebarProps {
  userId: string;
  sessions: ChatSession[];
  activeSessionId: string;
  onCreateSession: () => void;
  onLoadSession: (sessionId: string) => void;
  onSettingsClick: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  userId,
  sessions,
  activeSessionId,
  onCreateSession,
  onLoadSession,
  onSettingsClick,
}) => {
  return (
    <aside className="w-72 flex flex-col z-10 border-r border-[#e8dcc4] bg-white/20 backdrop-blur-2xl">
      {/* 顶部Logo */}
      <div className="p-6 flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-[#d4af37] to-[#aa8c2c] rounded-full flex items-center justify-center shadow-lg">
          <BookOpen className="text-white w-5 h-5" />
        </div>
        <h1 className="text-xl font-bold tracking-tight text-[#2c241d] italic">MacAgent</h1>
      </div>

      {/* 新建会话按钮 */}
      <div className="px-4 mb-4">
        <button 
          type="button"
          onClick={onCreateSession}
          className="w-full py-3 px-4 rounded-xl bg-[#f5efe1] border border-[#d4af37]/30 flex items-center justify-center gap-2 hover:bg-[#eaddc0] transition-all group shadow-sm"
        >
          <Plus className="w-4 h-4 text-[#d4af37] group-hover:rotate-90 transition-transform" />
          <span className="text-sm font-semibold">开启新篇章</span>
        </button>
      </div>

      {/* 用户信息 */}
      <div className="mb-6 px-4">
        <div className="text-[10px] uppercase tracking-[0.2em] text-[#a08b73] font-bold mb-2">用户信息</div>
        <div className="text-xs text-[#4a3f35] break-all opacity-70">{userId || '生成中...'}</div>
      </div>

      {/* 历史记录 */}
      <nav className="flex-1 overflow-y-auto px-2 space-y-1">
        <div className="px-4 py-2 text-[10px] uppercase tracking-[0.2em] text-[#a08b73] font-bold">近期回溯</div>
        {sessions.length === 0 ? (
          <div className="px-4 py-3 text-sm text-[#a08b73]">暂无会话</div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`group flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-all hover:bg-[#fcf8ef] ${
                session.id === activeSessionId ? 'bg-[#fcf8ef] border-l-4 border-[#d4af37]' : ''
              }`}
              onClick={() => onLoadSession(session.id)}
            >
              <MessageSquare className="w-4 h-4 text-[#a08b73]" />
              <span className="text-sm truncate opacity-80">{session.title || '新会话'}</span>
            </div>
          ))
        )}
      </nav>

      {/* 底部用户卡片 + 设置按钮 */}
      <div className="p-4 border-t border-[#e8dcc4] flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-200 to-amber-100 flex items-center justify-center text-[10px] text-gray-700 border-2 border-[#d4af37]">
          MA
        </div>
        <div className="flex-1">
          <p className="text-xs font-bold">MacAgent</p>
          <p className="text-[10px] opacity-50">智能助手</p>
        </div>
        <button
          type="button"
          onClick={onSettingsClick}
          className="p-2 rounded-lg hover:bg-[#f5efe1] transition-colors"
          title="打开设置"
        >
          <Settings className="w-4 h-4 opacity-40 hover:opacity-100 transition-opacity" />
        </button>
      </div>
    </aside>
  );
};
