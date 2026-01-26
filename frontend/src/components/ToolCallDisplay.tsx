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
    running: <Loader2 className="w-4 h-4 animate-spin text-blue-500" />,
    completed: <CheckCircle className="w-4 h-4 text-green-500" />,
    failed: <XCircle className="w-4 h-4 text-red-500" />,
  };

  return (
    <div className="border border-gray-200 rounded-md my-2 overflow-hidden bg-white shadow-sm">
      <div 
        className="flex items-center gap-2 p-2 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? <ChevronDown className="w-4 h-4 text-gray-500" /> : <ChevronRight className="w-4 h-4 text-gray-500" />}
        <Terminal className="w-4 h-4 text-gray-600" />
        <span className="font-mono text-sm font-medium text-gray-700">{tool.name}</span>
        <div className="flex-1" />
        {statusIcon[tool.status]}
      </div>
      
      {isExpanded && (
        <div className="p-3 text-xs font-mono border-t border-gray-200">
          <div className="mb-2">
            <div className="text-gray-500 mb-1 uppercase tracking-wider text-[10px]">Arguments</div>
            <div className="bg-gray-50 p-2 rounded text-gray-800 overflow-x-auto">
              <pre>{JSON.stringify(tool.args, null, 2)}</pre>
            </div>
          </div>
          
          {tool.result !== undefined && (
            <div>
              <div className="text-gray-500 mb-1 uppercase tracking-wider text-[10px]">Result</div>
              <div className={clsx("p-2 rounded overflow-x-auto", 
                tool.status === 'failed' ? "bg-red-50 text-red-800" : "bg-gray-50 text-gray-800"
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
