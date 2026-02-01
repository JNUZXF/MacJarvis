/**
 * File: frontend/src/components/VoiceButton.tsx
 * Path: frontend/src/components/VoiceButton.tsx
 * Purpose: 语音识别录音按钮组件，支持手动停止和自动静音检测
 */

import React from 'react';
import { Mic, MicOff } from 'lucide-react';
import { useVoiceRecognition } from '../utils/use-voice-recognition';
import styles from './VoiceButton.module.css';

interface VoiceButtonProps {
  apiUrl: string;
  onTranscriptUpdate?: (text: string) => void;
  onAutoSend?: (text: string) => void;
  disabled?: boolean;
}

export const VoiceButton: React.FC<VoiceButtonProps> = ({
  apiUrl,
  onTranscriptUpdate,
  onAutoSend,
  disabled = false,
}) => {
  const {
    isRecording,
    transcript,
    isSilent,
    silenceCountdown,
    error,
    volume,
    startRecording,
    stopRecording,
  } = useVoiceRecognition({
    apiUrl,
    silenceThreshold: 0.01,
    silenceDuration: 3000,
    onTranscript: (text) => {
      // 实时更新输入框
      if (onTranscriptUpdate) {
        onTranscriptUpdate(transcript + text);
      }
    },
    onComplete: (finalText) => {
      // 3秒静音后自动发送
      if (onAutoSend && finalText) {
        onAutoSend(finalText);
      }
    },
    onError: (errorMsg) => {
      console.error('Voice recognition error:', errorMsg);
      alert(`语音识别错误: ${errorMsg}`);
    },
  });

  // 更新输入框内容
  React.useEffect(() => {
    if (transcript && onTranscriptUpdate) {
      onTranscriptUpdate(transcript);
    }
  }, [transcript, onTranscriptUpdate]);

  const handleClick = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  // 计算音量指示器的缩放比例
  const volumeScale = 1 + volume * 2;

  return (
    <div className={styles.container}>
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled}
        className={`${styles.button} ${isRecording ? styles.recording : ''} ${
          disabled ? styles.disabled : ''
        }`}
        title={isRecording ? '点击停止录音' : '点击开始录音'}
      >
        {/* 音量波纹效果 */}
        {isRecording && (
          <div
            className={styles.volumeRipple}
            style={{
              transform: `scale(${volumeScale})`,
              opacity: volume > 0.01 ? 0.6 : 0.2,
            }}
          />
        )}

        {/* 图标 */}
        {isRecording ? (
          <MicOff className={styles.icon} />
        ) : (
          <Mic className={styles.icon} />
        )}
      </button>

      {/* 静音倒计时提示 */}
      {isRecording && isSilent && silenceCountdown > 0 && (
        <div className={styles.countdown}>
          {silenceCountdown}秒后自动发送...
        </div>
      )}

      {/* 录音状态提示 */}
      {isRecording && !isSilent && (
        <div className={styles.statusHint}>
          正在录音...
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className={styles.error}>
          {error}
        </div>
      )}
    </div>
  );
};
