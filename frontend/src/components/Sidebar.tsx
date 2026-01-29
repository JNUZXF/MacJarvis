// 左侧边栏组件
// 路径: frontend/src/components/Sidebar.tsx
// 功能: 显示用户信息、新建会话按钮、历史聊天记录、设置入口

import React from 'react';
import { Plus, MessageSquare, BookOpen, Settings } from 'lucide-react';
import type { ChatSession } from '../types';
import styles from './Sidebar.module.css';

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
    <aside className={styles.sidebar}>
      {/* 顶部Logo */}
      <div className={styles.logo}>
        <div className={styles.logoIcon}>
          <BookOpen className="text-white w-5 h-5" />
        </div>
        <h1 className={styles.logoText}>MacAgent</h1>
      </div>

      {/* 新建会话按钮 */}
      <div className="px-4 mb-4">
        <button 
          type="button"
          onClick={onCreateSession}
          className={`${styles.newChatButton} group`}
        >
          <Plus className={`w-4 h-4 text-[#d4af37] ${styles.newChatButtonIcon} group-hover:rotate-90`} />
          <span className="text-sm font-semibold">新建聊天</span>
        </button>
      </div>

      {/* 用户信息 */}
      <div className={styles.userInfo}>
        <div className={styles.userInfoLabel}>用户信息</div>
        <div className={styles.userInfoValue}>{userId || '生成中...'}</div>
      </div>

      {/* 历史记录 */}
      <nav className={styles.sessionList}>
        <div className={styles.sessionListLabel}>近期回溯</div>
        {sessions.length === 0 ? (
          <div className={styles.emptySessions}>暂无会话</div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`${styles.sessionItem} ${session.id === activeSessionId ? styles.activeSession : ''}`}
              onClick={() => onLoadSession(session.id)}
            >
              <MessageSquare className={styles.sessionIcon} />
              <span className={styles.sessionTitle}>{session.title || '新会话'}</span>
            </div>
          ))
        )}
      </nav>

      {/* 底部用户卡片 + 设置按钮 */}
      <div className={styles.footer}>
        <div className={styles.userAvatar}>
          MA
        </div>
        <div className={styles.userInfoFooter}>
          <p className={styles.userName}>MacAgent</p>
          <p className={styles.userRole}>智能助手</p>
        </div>
        <button
          type="button"
          onClick={onSettingsClick}
          className={styles.settingsButton}
          title="打开设置"
        >
          <Settings className={styles.settingsIcon} />
        </button>
      </div>
    </aside>
  );
};
