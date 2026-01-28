// 设置页面组件
// 路径: frontend/src/components/Settings.tsx
// 功能: 集中管理所有配置（路径白名单、代理配置、模型选择等）

import React, { useState } from 'react';
import { X, Plus } from 'lucide-react';

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
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* 头部 */}
        <div className="sticky top-0 flex items-center justify-between p-6 border-b border-[#e8dcc4] bg-white">
          <h2 className="text-2xl font-bold text-[#2c241d]">系统设置</h2>
          <button
            type="button"
            onClick={onClose}
            className="p-2 hover:bg-[#f5efe1] rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-[#a08b73]" />
          </button>
        </div>

        {/* 内容区 */}
        <div className="p-6 space-y-8">
          {/* 模型选择 */}
          <div>
            <h3 className="text-lg font-bold text-[#2c241d] mb-4 flex items-center gap-2">
              <span className="w-1 h-6 bg-[#d4af37] rounded"></span>
              模型选择
            </h3>
            <div className="space-y-2">
              <label className="text-sm text-[#4a3f35] font-semibold">当前模型</label>
              <select
                value={model}
                onChange={(e) => onModelChange(e.target.value)}
                className="w-full px-4 py-2 rounded-lg border border-[#e8dcc4] bg-white text-[#4a3f35] focus:border-[#d4af37] focus:ring-2 focus:ring-[#d4af37]/30 outline-none transition-all"
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
          <div>
            <h3 className="text-lg font-bold text-[#2c241d] mb-4 flex items-center gap-2">
              <span className="w-1 h-6 bg-[#d4af37] rounded"></span>
              路径白名单
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-[#4a3f35] font-semibold block mb-2">快速添加</label>
                <div className="flex flex-wrap gap-2">
                  {['~', '~/Desktop', '~/Documents', '~/Downloads'].map((path) => (
                    <button
                      key={path}
                      type="button"
                      onClick={() => handleQuickAdd(path)}
                      className={`px-3 py-2 rounded-lg border text-sm transition-all ${
                        userPaths.includes(path)
                          ? 'bg-[#d4af37] text-white border-[#d4af37]'
                          : 'bg-[#f5efe1] text-[#4a3f35] border-[#e8dcc4] hover:border-[#d4af37]'
                      }`}
                    >
                      {path}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm text-[#4a3f35] font-semibold block mb-2">自定义路径</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={pathInput}
                    onChange={(e) => setPathInput(e.target.value)}
                    placeholder="输入绝对路径或~"
                    className="flex-1 px-4 py-2 rounded-lg border border-[#e8dcc4] bg-white text-[#4a3f35] placeholder-[#a08b73]/50 focus:border-[#d4af37] focus:ring-2 focus:ring-[#d4af37]/30 outline-none transition-all"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleAddPath();
                      }
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleAddPath}
                    className="px-4 py-2 rounded-lg bg-[#d4af37] hover:bg-[#aa8c2c] text-white font-semibold transition-colors flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    添加
                  </button>
                </div>
              </div>

              {pathError && (
                <div className="text-sm text-red-600 bg-red-50 p-3 rounded-lg">{pathError}</div>
              )}

              <div>
                <label className="text-sm text-[#4a3f35] font-semibold block mb-2">已配置路径</label>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {userPaths.length === 0 ? (
                    <div className="text-sm text-[#a08b73] py-3 text-center bg-[#f5efe1] rounded-lg">
                      未配置任何路径
                    </div>
                  ) : (
                    userPaths.map((path) => (
                      <div
                        key={path}
                        className="flex items-center justify-between p-3 bg-[#f5efe1] rounded-lg border border-[#e8dcc4]"
                      >
                        <span className="text-sm text-[#4a3f35] truncate" title={path}>
                          {path}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleRemovePath(path)}
                          className="text-red-400 hover:text-red-600 text-sm font-semibold transition-colors"
                        >
                          移除
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <p className="text-xs text-[#a08b73] bg-blue-50 p-3 rounded-lg border border-blue-200">
                🔒 <strong>安全限制：</strong>系统仅允许访问配置的路径中的文件，防止不当访问。
              </p>
            </div>
          </div>

          {/* 代理配置 */}
          <div>
            <h3 className="text-lg font-bold text-[#2c241d] mb-4 flex items-center gap-2">
              <span className="w-1 h-6 bg-[#d4af37] rounded"></span>
              代理配置 (可选)
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-[#4a3f35] font-semibold block mb-2">HTTP 代理</label>
                <input
                  type="text"
                  value={httpProxy}
                  onChange={(e) => onHttpProxyChange(e.target.value)}
                  placeholder="http://127.0.0.1:7897"
                  className="w-full px-4 py-2 rounded-lg border border-[#e8dcc4] bg-white text-[#4a3f35] placeholder-[#a08b73]/50 focus:border-[#d4af37] focus:ring-2 focus:ring-[#d4af37]/30 outline-none transition-all"
                />
              </div>

              <div>
                <label className="text-sm text-[#4a3f35] font-semibold block mb-2">HTTPS 代理</label>
                <input
                  type="text"
                  value={httpsProxy}
                  onChange={(e) => onHttpsProxyChange(e.target.value)}
                  placeholder="http://127.0.0.1:7897"
                  className="w-full px-4 py-2 rounded-lg border border-[#e8dcc4] bg-white text-[#4a3f35] placeholder-[#a08b73]/50 focus:border-[#d4af37] focus:ring-2 focus:ring-[#d4af37]/30 outline-none transition-all"
                />
              </div>

              <button
                type="button"
                onClick={onSaveProxy}
                className="w-full px-4 py-3 rounded-lg bg-[#d4af37] hover:bg-[#aa8c2c] text-white font-bold transition-colors"
              >
                保存代理配置
              </button>

              {proxyError && (
                <div className="text-sm text-red-600 bg-red-50 p-3 rounded-lg">{proxyError}</div>
              )}

              <p className="text-xs text-[#a08b73] bg-green-50 p-3 rounded-lg border border-green-200">
                💡 <strong>代理加速：</strong>配置代理可加速API请求，特别是在网络受限的环境中。留空则不使用代理。支持 Clash、V2Ray 等工具。
              </p>
            </div>
          </div>
        </div>

        {/* 底部 */}
        <div className="sticky bottom-0 p-6 border-t border-[#e8dcc4] bg-white flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-6 py-2 rounded-lg border border-[#e8dcc4] text-[#4a3f35] font-semibold hover:bg-[#f5efe1] transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};
