import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { User, Bot } from 'lucide-react';
import type { Message } from '../types';
import { ToolCallDisplay } from './ToolCallDisplay';
import clsx from 'clsx';

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={clsx("flex gap-4 p-6", isUser ? "bg-white" : "bg-gray-50/50")}>
      <div className={clsx(
        "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
        isUser ? "bg-gray-200" : "bg-blue-600"
      )}>
        {isUser ? <User className="w-5 h-5 text-gray-600" /> : <Bot className="w-5 h-5 text-white" />}
      </div>
      
      <div className="flex-1 overflow-hidden">
        <div className="font-semibold text-sm text-gray-900 mb-1">
          {isUser ? 'You' : 'Agent'}
        </div>
        
        <div className="prose prose-sm max-w-none text-gray-800 dark:prose-invert mb-4">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>

        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="space-y-2">
            {message.toolCalls.map((tool) => (
              <ToolCallDisplay key={tool.id} tool={tool} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
