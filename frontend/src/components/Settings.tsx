// 设置页面组件
// 路径: frontend/src/components/Settings.tsx
// 功能: 集中管理所有配置（路径白名单、代理配置、模型选择等）

import React, { useState } from 'react';
import { X, Plus } from 'lucide-react';
import styles from './Settings.module.css';
import clsx from 'clsx';

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
}) => {
  const [pathInput, setPathInput] = useState('');

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
