import React, { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle, XCircle, Loader2, Terminal } from 'lucide-react';
import type { ToolCall } from '../types';
import clsx from 'clsx';

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
    <div className="border border-[#e8dcc4] rounded-xl my-2 overflow-hidden bg-white/50 backdrop-blur-sm shadow-sm">
      <div 
        className="flex items-center gap-2 p-3 bg-[#fdfbf7]/80 cursor-pointer hover:bg-[#f5efe1] transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? <ChevronDown className="w-4 h-4 text-[#a08b73]" /> : <ChevronRight className="w-4 h-4 text-[#a08b73]" />}
        <Terminal className="w-4 h-4 text-[#d4af37]" />
        <span className="font-mono text-sm font-medium text-[#4a3f35]">{tool.name}</span>
        <div className="flex-1" />
        {statusIcon[tool.status]}
      </div>
      
      {isExpanded && (
        <div className="p-3 text-xs font-mono border-t border-[#e8dcc4]">
          <div className="mb-2">
            <div className="text-[#a08b73] mb-1 uppercase tracking-wider text-[10px] font-bold">参数</div>
            <div className="bg-[#f5efe1] p-2 rounded-lg text-[#4a3f35] overflow-x-auto border border-[#e8dcc4]">
              <pre>{JSON.stringify(tool.args, null, 2)}</pre>
            </div>
          </div>
          
          {tool.result !== undefined && (
            <div>
              <div className="text-[#a08b73] mb-1 uppercase tracking-wider text-[10px] font-bold">结果</div>
              <div className={clsx("p-2 rounded-lg overflow-x-auto border", 
                tool.status === 'failed' 
                  ? "bg-red-50 text-red-800 border-red-200" 
                  : "bg-[#f5efe1] text-[#4a3f35] border-[#e8dcc4]"
              )}>
                <pre>{JSON.stringify(tool.result, null, 2)}</pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
