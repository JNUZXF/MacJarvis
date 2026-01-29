import React, { memo, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import { Sparkles } from 'lucide-react';
import type { Message, MessageBlock } from '../types';
import { ToolCallDisplay } from './ToolCallDisplay';
import { ErrorBoundary } from './ErrorBoundary';
import clsx from 'clsx';
import styles from './ChatMessage.module.css';
import markdownStyles from '../styles/markdown.module.css';
import 'highlight.js/styles/atom-one-dark.css';

interface ChatMessageProps {
  message: Message;
}

// 使用 memo 优化性能，避免不必要的重渲染
export const ChatMessage: React.FC<ChatMessageProps> = memo(({ message }) => {
  const isUser = message.role === 'user';
  const toolCalls = message.toolCalls ?? [];
  
  // 使用 useMemo 缓存 blocks 计算结果
  const blocks: MessageBlock[] = useMemo(() => {
    if (message.blocks) {
      return message.blocks;
    }
    return [
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
  }, [message.blocks, message.content, toolCalls]);

  // 检测是否包含工具调用，实现自适应宽度
  const hasToolCalls = toolCalls.length > 0;

  // 自定义 markdown 组件，避免循环引用
  const markdownComponents = useMemo(() => ({
    // 自定义链接组件
    a: ({ node, ...props }: any) => (
      <a {...props} target="_blank" rel="noopener noreferrer" />
    ),
    // 自定义输入组件（任务列表）
    input: ({ node, ...props }: any) => (
      <input {...props} disabled={props.type === 'checkbox'} />
    ),
    // 自定义代码块组件，限制最大高度
    pre: ({ node, ...props }: any) => (
      <pre {...props} style={{ maxHeight: '500px', overflowY: 'auto' }} />
    ),
  }), []);

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
                // 如果内容为空，跳过渲染
                if (!block.content || block.content.trim() === '') {
                  return null;
                }
                
                return (
                  <ErrorBoundary key={`content-${index}`}>
                    <div className={markdownStyles.markdownContent}>
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm, remarkBreaks]}
                        rehypePlugins={[rehypeRaw, rehypeHighlight]}
                        components={markdownComponents}
                      >
                        {block.content}
                      </ReactMarkdown>
                    </div>
                  </ErrorBoundary>
                );
              }

              if (block.type === 'tool') {
                const tool = toolCalls.find((item) => item.id === block.toolCallId);
                if (!tool) return null;
                return (
                  <ErrorBoundary key={tool.id}>
                    <ToolCallDisplay tool={tool} />
                  </ErrorBoundary>
                );
              }

              return null;
            })}
          </div>
        </div>
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  // 自定义比较函数，只有当消息内容真正变化时才重新渲染
  return (
    prevProps.message.id === nextProps.message.id &&
    prevProps.message.content === nextProps.message.content &&
    prevProps.message.toolCalls?.length === nextProps.message.toolCalls?.length &&
    prevProps.message.blocks?.length === nextProps.message.blocks?.length
  );
});
