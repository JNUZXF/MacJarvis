/**
 * 错误边界组件
 * 路径: frontend/src/components/ErrorBoundary.tsx
 * 功能: 捕获子组件渲染错误，防止整个应用崩溃白屏
 */

import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { AlertCircle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-red-800 mb-1">
                渲染错误
              </h3>
              <p className="text-xs text-red-600 mb-2">
                {this.state.error?.message || '组件渲染时发生错误'}
              </p>
              {import.meta.env.DEV && this.state.errorInfo && (
                <details className="text-xs text-red-500 mb-2">
                  <summary className="cursor-pointer hover:underline">
                    查看详细信息
                  </summary>
                  <pre className="mt-2 p-2 bg-red-100 rounded overflow-auto max-h-40 text-[10px]">
                    {this.state.errorInfo.componentStack}
                  </pre>
                </details>
              )}
              <button
                onClick={this.handleReset}
                className="text-xs px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
              >
                重试
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
