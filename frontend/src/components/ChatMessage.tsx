import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Sparkles } from 'lucide-react';
import type { Message, MessageBlock } from '../types';
import { ToolCallDisplay } from './ToolCallDisplay';
import clsx from 'clsx';

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const toolCalls = message.toolCalls ?? [];
  const blocks: MessageBlock[] = message.blocks
    ? message.blocks
    : [
        ...(message.content
          ? [
              {
                type: 'content' as const,
                content: message.content,
              },
            ]
          : []),
        ...toolCalls.map((tool) => ({
          type: 'tool' as const,
          toolCallId: tool.id,
        })),
      ];

  return (
    <div className={clsx("flex", isUser ? "justify-end" : "justify-start")}>
      <div className={clsx("max-w-[80%] group", isUser ? "order-1" : "")}>
        <div className={clsx(
          "relative p-5 rounded-3xl shadow-sm border transition-transform hover:scale-[1.01]",
          isUser 
            ? "bg-[#f5efe1] border-[#d4af37]/20 rounded-tr-none text-[#4a3f35]" 
            : "bg-white/60 backdrop-blur-xl border-white/40 rounded-tl-none text-[#2c241d]"
        )}>
          {!isUser && (
            <div className="absolute -top-4 -left-2 bg-white rounded-full p-1 shadow-md border border-[#eee]">
              <Sparkles className="w-3 h-3 text-[#d4af37]" />
            </div>
          )}
          
          <div className="space-y-3">
            {blocks.map((block, index) => {
              if (block.type === 'content') {
                return (
                  <div
                    key={`content-${index}`}
                    className="prose prose-sm max-w-none text-[#2c241d] prose-headings:text-[#2c241d] prose-p:text-[#4a3f35] prose-strong:text-[#2c241d] prose-code:text-[#d4af37] prose-pre:bg-[#f5efe1] prose-pre:border prose-pre:border-[#e8dcc4]"
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {block.content}
                    </ReactMarkdown>
                  </div>
                );
              }

              const tool = toolCalls.find((item) => item.id === block.toolCallId);
              if (!tool) return null;
              return <ToolCallDisplay key={tool.id} tool={tool} />;
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
