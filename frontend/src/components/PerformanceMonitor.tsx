/**
 * 性能监控组件
 * 路径: frontend/src/components/PerformanceMonitor.tsx
 * 功能: 监控组件渲染性能，帮助诊断性能问题
 */

import { useEffect, useRef } from 'react';

interface PerformanceMonitorProps {
  componentName: string;
  enabled?: boolean;
}

export const PerformanceMonitor: React.FC<PerformanceMonitorProps> = ({ 
  componentName, 
  enabled = import.meta.env.DEV 
}) => {
  const renderCount = useRef(0);
  const lastRenderTime = useRef(Date.now());

  useEffect(() => {
    if (!enabled) return;

    renderCount.current += 1;
    const now = Date.now();
    const timeSinceLastRender = now - lastRenderTime.current;
    lastRenderTime.current = now;

    // 如果渲染间隔小于 16ms (60fps)，可能存在过度渲染
    if (timeSinceLastRender < 16 && renderCount.current > 1) {
      console.warn(
        `[Performance] ${componentName} 渲染过于频繁`,
        `渲染次数: ${renderCount.current}`,
        `距上次渲染: ${timeSinceLastRender}ms`
      );
    }

    // 每 100 次渲染输出一次统计
    if (renderCount.current % 100 === 0) {
      console.log(
        `[Performance] ${componentName} 已渲染 ${renderCount.current} 次`
      );
    }
  });

  return null;
};
