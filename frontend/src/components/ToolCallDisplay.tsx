import React, { useState, memo, useMemo } from 'react';
import { ChevronDown, ChevronRight, CheckCircle, XCircle, Loader2, Terminal } from 'lucide-react';
import type { ToolCall } from '../types';
import clsx from 'clsx';
import styles from './ToolCallDisplay.module.css';

interface ToolCallProps {
  tool: ToolCall;
}

// 安全的 JSON 字符串化函数，避免循环引用和过大的对象
const safeStringify = (obj: any, maxLength: number = 10000): string => {
  try {
    const cache = new Set();
    const result = JSON.stringify(
      obj,
      (_key, value) => {
        // 处理循环引用
        if (typeof value === 'object' && value !== null) {
          if (cache.has(value)) {
            return '[Circular Reference]';
          }
          cache.add(value);
        }
        return value;
      },
      2
    );
    
    // 如果结果太长，截断并添加提示
    if (result.length > maxLength) {
      return result.substring(0, maxLength) + '\n\n... (内容过长，已截断)';
    }
    
    return result;
  } catch (error) {
    console.error('JSON stringify error:', error);
    return `[无法序列化: ${error instanceof Error ? error.message : String(error)}]`;
  }
};

// 使用 memo 优化性能
export const ToolCallDisplay: React.FC<ToolCallProps> = memo(({ tool }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const statusIcon = useMemo(() => ({
    running: <Loader2 className="w-4 h-4 animate-spin text-[#d4af37]" />,
    completed: <CheckCircle className="w-4 h-4 text-green-500" />,
    failed: <XCircle className="w-4 h-4 text-red-500" />,
  }), []);

  // 缓存序列化结果，避免重复计算
  const argsString = useMemo(() => safeStringify(tool.args), [tool.args]);
  const resultString = useMemo(() => 
    tool.result !== undefined ? safeStringify(tool.result) : null,
    [tool.result]
  );

  return (
    <div className={styles.toolContainer}>
      <div 
        className={styles.toolHeader}
        onClick={() => setIsExpanded(!isExpanded)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsExpanded(!isExpanded);
          }
        }}
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-[#a08b73]" />
        ) : (
          <ChevronRight className="w-4 h-4 text-[#a08b73]" />
        )}
        <Terminal className="w-4 h-4 text-[#d4af37]" />
        <span className="font-mono text-sm font-medium text-[#4a3f35]">
          {tool.name || '未知工具'}
        </span>
        <div className="flex-1" />
        {statusIcon[tool.status]}
      </div>
      
      {isExpanded && (
        <div className={styles.toolContent}>
          <div className={styles.paramSection}>
            <div className={styles.paramLabel}>参数</div>
            <div className={styles.paramContainer}>
              <pre className={styles.codeBlock}>{argsString}</pre>
            </div>
          </div>
          
          {resultString !== null && (
            <div className={styles.resultSection}>
              <div className={styles.resultLabel}>结果</div>
              <div className={clsx(
                styles.resultContainer,
                tool.status === 'failed' ? styles.resultContainerFailed : styles.resultContainerSuccess
              )}>
                <pre className={styles.codeBlock}>{resultString}</pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}, (prevProps, nextProps) => {
  // 只有当工具状态真正变化时才重新渲染
  return (
    prevProps.tool.id === nextProps.tool.id &&
    prevProps.tool.status === nextProps.tool.status &&
    prevProps.tool.result === nextProps.tool.result
  );
});
