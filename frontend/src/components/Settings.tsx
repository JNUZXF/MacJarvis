// 设置页面组件
// 路径: frontend/src/components/Settings.tsx
// 功能: 集中管理所有配置（路径白名单、代理配置、模型选择等）

import React, { useState } from 'react';
import { X, Plus } from 'lucide-react';
import styles from './Settings.module.css';
import clsx from 'clsx';
import { TTSSettings } from './TTSSettings';
import type { TTSConfig } from '../types';

interface SettingsProps {
  isOpen: boolean;
  onClose: () => void;
  model: string;
  onModelChange: (model: string) => void;
  modelOptions: Array<{ value: string; label: string }>;
  userPaths: string[];
  onPathsChange: (paths: string[]) => void;
  pathError: string;
  httpProxy: string;
  onHttpProxyChange: (proxy: string) => void;
  httpsProxy: string;
  onHttpsProxyChange: (proxy: string) => void;
  proxyError: string;
  onSaveProxy: () => void;
  ttsConfig: TTSConfig;
  onTTSConfigChange: (config: Partial<TTSConfig>) => void;
  apiUrl: string;
  userId: string;
  onClearAllSessions: () => void;
}

export const Settings: React.FC<SettingsProps> = ({
  isOpen,
  onClose,
  model,
  onModelChange,
  modelOptions,
  userPaths,
  onPathsChange,
  pathError,
  httpProxy,
  onHttpProxyChange,
  httpsProxy,
  onHttpsProxyChange,
  proxyError,
  onSaveProxy,
  ttsConfig,
  onTTSConfigChange,
  apiUrl,
  userId,
  onClearAllSessions,
}) => {
  const [pathInput, setPathInput] = useState('');
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  if (!isOpen) return null;

  const handleAddPath = () => {
    const nextPath = pathInput.trim();
    if (!nextPath) return;
    onPathsChange([...userPaths, nextPath]);
    setPathInput('');
  };

  const handleRemovePath = (path: string) => {
    onPathsChange(userPaths.filter((item) => item !== path));
  };

  const handleQuickAdd = (path: string) => {
    if (!userPaths.includes(path)) {
      onPathsChange([...userPaths, path]);
    }
  };

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        {/* 头部 */}
        <div className={styles.header}>
          <h2 className={styles.headerTitle}>系统设置</h2>
          <button
            type="button"
            onClick={onClose}
            className={styles.closeButton}
          >
            <X className={styles.closeIcon} />
          </button>
        </div>

        {/* 内容区 */}
        <div className={styles.content}>
          {/* 模型选择 */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>
              <span className={styles.sectionTitleIndicator}></span>
              模型选择
            </h3>
            <div className="space-y-2">
              <label className={styles.label}>当前模型</label>
              <select
                value={model}
                onChange={(e) => onModelChange(e.target.value)}
                className={styles.select}
              >
                {modelOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <p className="text-xs text-[#a08b73] mt-2">
                💡 选择合适的模型可以改善响应质量和速度。GPT-4o-mini 成本最低，Claude Haiku 推理能力强。
              </p>
            </div>
          </div>

          {/* 路径白名单 */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>
              <span className={styles.sectionTitleIndicator}></span>
              路径白名单
            </h3>
            <div className="space-y-4">
              <div>
                <label className={styles.label}>快速添加</label>
                <div className={styles.quickAddButtons}>
                  {['~', '~/Desktop', '~/Documents', '~/Downloads'].map((path) => (
                    <button
                      key={path}
                      type="button"
                      onClick={() => handleQuickAdd(path)}
                      className={clsx(
                        styles.quickAddButton,
                        userPaths.includes(path) ? styles.quickAddButtonActive : styles.quickAddButtonInactive
                      )}
                    >
                      {path}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className={styles.label}>自定义路径</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={pathInput}
                    onChange={(e) => setPathInput(e.target.value)}
                    placeholder="输入绝对路径或~"
                    className={clsx(styles.input, "flex-1")}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleAddPath();
                      }
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleAddPath}
                    className={clsx(styles.button, styles.buttonPrimary)}
                  >
                    <Plus className="w-4 h-4" />
                    添加
                  </button>
                </div>
              </div>

              {pathError && (
                <div className={styles.errorMessage}>{pathError}</div>
              )}

              <div>
                <label className={styles.label}>已配置路径</label>
                <div className={styles.pathList}>
                  {userPaths.length === 0 ? (
                    <div className={styles.emptyState}>
                      未配置任何路径
                    </div>
                  ) : (
                    userPaths.map((path) => (
                      <div
                        key={path}
                        className={styles.pathItem}
                      >
                        <span className={styles.pathText} title={path}>
                          {path}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleRemovePath(path)}
                          className={styles.removeButton}
                        >
                          移除
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <p className={clsx(styles.infoBox, styles.infoBoxBlue)}>
                🔒 <strong>安全限制：</strong>系统仅允许访问配置的路径中的文件，防止不当访问。
              </p>
            </div>
          </div>

          {/* 代理配置 */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>
              <span className={styles.sectionTitleIndicator}></span>
              代理配置 (可选)
            </h3>
            <div className="space-y-4">
              <div>
                <label className={styles.label}>HTTP 代理</label>
                <input
                  type="text"
                  value={httpProxy}
                  onChange={(e) => onHttpProxyChange(e.target.value)}
                  placeholder="http://127.0.0.1:7897"
                  className={styles.input}
                />
              </div>

              <div>
                <label className={styles.label}>HTTPS 代理</label>
                <input
                  type="text"
                  value={httpsProxy}
                  onChange={(e) => onHttpsProxyChange(e.target.value)}
                  placeholder="http://127.0.0.1:7897"
                  className={styles.input}
                />
              </div>

              <button
                type="button"
                onClick={onSaveProxy}
                className={clsx(styles.button, styles.buttonPrimary, "w-full")}
              >
                保存代理配置
              </button>

              {proxyError && (
                <div className={styles.errorMessage}>{proxyError}</div>
              )}

              <p className={clsx(styles.infoBox, styles.infoBoxGreen)}>
                💡 <strong>代理加速：</strong>配置代理可加速API请求，特别是在网络受限的环境中。留空则不使用代理。支持 Clash、V2Ray 等工具。
              </p>
            </div>
          </div>

          {/* TTS 设置 */}
          <div className={styles.section}>
            <TTSSettings
              config={ttsConfig}
              apiUrl={apiUrl}
              onConfigChange={onTTSConfigChange}
            />
          </div>

          {/* 数据管理 */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>
              <span className={styles.sectionTitleIndicator}></span>
              数据管理
            </h3>
            <div className="space-y-4">
              <div>
                <label className={styles.label}>用户标识</label>
                <div className={styles.input} style={{ backgroundColor: '#f5f5f5', cursor: 'not-allowed' }}>
                  {userId ? `${userId.substring(0, 16)}...` : '未初始化'}
                </div>
                <p className="text-xs text-[#a08b73] mt-2">
                  💡 基于机器硬件生成的唯一标识，确保聊天记录绑定到本机
                </p>
              </div>

              <div>
                <label className={styles.label}>清除所有聊天记录</label>
                {!showClearConfirm ? (
                  <button
                    type="button"
                    onClick={() => setShowClearConfirm(true)}
                    className={clsx(styles.button, "w-full")}
                    style={{ 
                      backgroundColor: '#dc2626',
                      color: 'white',
                      borderColor: '#dc2626'
                    }}
                  >
                    清除所有聊天记录
                  </button>
                ) : (
                  <div className="space-y-2">
                    <div className={styles.errorMessage}>
                      ⚠️ 此操作将删除所有会话和消息，不可恢复！
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          onClearAllSessions();
                          setShowClearConfirm(false);
                        }}
                        className={clsx(styles.button, "flex-1")}
                        style={{ 
                          backgroundColor: '#dc2626',
                          color: 'white',
                          borderColor: '#dc2626'
                        }}
                      >
                        确认清除
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowClearConfirm(false)}
                        className={clsx(styles.button, styles.buttonSecondary, "flex-1")}
                      >
                        取消
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <p className={clsx(styles.infoBox, styles.infoBoxBlue)}>
                🗑️ <strong>数据清除：</strong>清除所有聊天记录后，系统将自动创建新的会话。用户标识不会改变，路径配置和代理设置也会保留。
              </p>
            </div>
          </div>
        </div>

        {/* 底部 */}
        <div className={styles.footer}>
          <button
            type="button"
            onClick={onClose}
            className={clsx(styles.button, styles.buttonSecondary)}
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};
