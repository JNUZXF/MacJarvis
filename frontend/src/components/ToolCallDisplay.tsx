import React, { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle, XCircle, Loader2, Terminal } from 'lucide-react';
import type { ToolCall } from '../types';
import clsx from 'clsx';
import styles from './ToolCallDisplay.module.css';

interface ToolCallProps {
  tool: ToolCall;
}

export const ToolCallDisplay: React.FC<ToolCallProps> = ({ tool }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const statusIcon = {
    running: <Loader2 className="w-4 h-4 animate-spin text-[#d4af37]" />,
    completed: <CheckCircle className="w-4 h-4 text-green-500" />,
    failed: <XCircle className="w-4 h-4 text-red-500" />,
  };

  return (
    <div className={styles.toolContainer}>
      <div 
        className={styles.toolHeader}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? <ChevronDown className="w-4 h-4 text-[#a08b73]" /> : <ChevronRight className="w-4 h-4 text-[#a08b73]" />}
        <Terminal className="w-4 h-4 text-[#d4af37]" />
        <span className="font-mono text-sm font-medium text-[#4a3f35]">{tool.name}</span>
        <div className="flex-1" />
        {statusIcon[tool.status]}
      </div>
      
      {isExpanded && (
        <div className={styles.toolContent}>
          <div className={styles.paramSection}>
            <div className={styles.paramLabel}>参数</div>
            <div className={styles.paramContainer}>
              <pre className={styles.codeBlock}>{JSON.stringify(tool.args, null, 2)}</pre>
            </div>
          </div>
          
          {tool.result !== undefined && (
            <div className={styles.resultSection}>
              <div className={styles.resultLabel}>结果</div>
              <div className={clsx(
                styles.resultContainer,
                tool.status === 'failed' ? styles.resultContainerFailed : styles.resultContainerSuccess
              )}>
                <pre className={styles.codeBlock}>{JSON.stringify(tool.result, null, 2)}</pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
