import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import { Sparkles } from 'lucide-react';
import type { Message, MessageBlock } from '../types';
import { ToolCallDisplay } from './ToolCallDisplay';
import clsx from 'clsx';
import styles from './ChatMessage.module.css';
import markdownStyles from '../styles/markdown.module.css';
import 'highlight.js/styles/atom-one-dark.css';

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

  // 检测是否包含工具调用，实现自适应宽度
  const hasToolCalls = toolCalls.length > 0;

  return (
    <div className={clsx(
      styles.messageWrapper,
      isUser ? styles.messageWrapperUser : styles.messageWrapperAssistant
    )}>
      <div className={clsx(
        styles.messageContainer,
        hasToolCalls && styles.messageContainerWithTools
      )}>
        <div className={clsx(
          styles.messageBubble,
          isUser ? styles.userBubble : styles.assistantBubble
        )}>
          {!isUser && (
            <div className={styles.assistantIcon}>
              <Sparkles className="w-3 h-3 text-[#d4af37]" />
            </div>
          )}
          
          <div className={styles.contentArea}>
            {blocks.map((block, index) => {
              if (block.type === 'content') {
                return (
                  <div
                    key={`content-${index}`}
                    className={markdownStyles.markdownContent}
                  >
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm, remarkBreaks]}
                      rehypePlugins={[rehypeRaw, rehypeHighlight]}
                      components={{
                        // 自定义组件以支持更多功能
                        a: ({ ...props }) => {
                          // 移除 node 属性避免循环引用
                          const { node, ...restProps } = props as any;
                          return <a {...restProps} target="_blank" rel="noopener noreferrer" />;
                        },
                        // 支持任务列表
                        input: ({ ...props }) => {
                          const { node, ...restProps } = props as any;
                          return <input {...restProps} disabled={restProps.type === 'checkbox'} />;
                        },
                      }}
                    >
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
