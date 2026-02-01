/**
 * File: frontend/src/utils/use-voice-recognition.ts
 * Path: frontend/src/utils/use-voice-recognition.ts
 * Purpose: 语音识别 React Hook，封装 Web Audio API 和 WebSocket 通信逻辑
 */

import { useState, useRef, useCallback, useEffect } from 'react';

interface VoiceRecognitionOptions {
  apiUrl: string;
  silenceThreshold?: number;  // 静音阈值 (0-1)
  silenceDuration?: number;   // 静音持续时间(毫秒)
  onTranscript?: (text: string, isFinal: boolean) => void;
  onComplete?: (finalText: string) => void;
  onError?: (error: string) => void;
}

interface VoiceRecognitionState {
  isRecording: boolean;
  transcript: string;
  isSilent: boolean;
  silenceCountdown: number;  // 静音倒计时(秒)
  error: string | null;
  volume: number;  // 当前音量 (0-1)
}

/**
 * 将 Float32Array 音频数据转换为 Int16Array PCM 格式
 */
function floatTo16BitPCM(float32Array: Float32Array): Int16Array {
  const int16Array = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  return int16Array;
}

/**
 * 计算音频数据的 RMS (均方根) 值，用于音量检测
 */
function calculateRMS(audioData: Float32Array): number {
  let sum = 0;
  for (let i = 0; i < audioData.length; i++) {
    sum += audioData[i] * audioData[i];
  }
  return Math.sqrt(sum / audioData.length);
}

/**
 * 语音识别 Hook
 */
export function useVoiceRecognition(options: VoiceRecognitionOptions) {
  const {
    apiUrl,
    silenceThreshold = 0.01,
    silenceDuration = 3000,
    onTranscript,
    onComplete,
    onError,
  } = options;

  const [state, setState] = useState<VoiceRecognitionState>({
    isRecording: false,
    transcript: '',
    isSilent: false,
    silenceCountdown: 0,
    error: null,
    volume: 0,
  });

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const silenceStartTimeRef = useRef<number | null>(null);
  const countdownIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const accumulatedTextRef = useRef<string>('');  // 已完成的句子累积
  const currentSentenceRef = useRef<string>('');  // 当前正在识别的句子
  const currentSentenceIdRef = useRef<string>(''); // 当前句子ID

  /**
   * 清理资源
   */
  const cleanup = useCallback(() => {
    // 关闭 WebSocket
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'stop' }));
      }
      wsRef.current.close();
      wsRef.current = null;
    }

    // 停止音频处理
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    // 关闭音频上下文
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // 停止媒体流
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }

    // 清理定时器
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }

    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }

    silenceStartTimeRef.current = null;
  }, []);

  /**
   * 开始静音倒计时
   */
  const startSilenceCountdown = useCallback(() => {
    if (!silenceStartTimeRef.current) {
      silenceStartTimeRef.current = Date.now();
    }

    setState(prev => ({ ...prev, isSilent: true }));

    // 更新倒计时显示
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
    }

    countdownIntervalRef.current = setInterval(() => {
      if (silenceStartTimeRef.current) {
        const elapsed = Date.now() - silenceStartTimeRef.current;
        const remaining = Math.max(0, Math.ceil((silenceDuration - elapsed) / 1000));
        setState(prev => ({ ...prev, silenceCountdown: remaining }));
      }
    }, 100);

    // 设置自动停止定时器
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
    }

    silenceTimerRef.current = setTimeout(() => {
      // 3秒静音后自动停止并发送
      const finalText = accumulatedTextRef.current;
      stopRecording();
      if (onComplete && finalText) {
        onComplete(finalText);
      }
    }, silenceDuration);
  }, [silenceDuration, onComplete]);

  /**
   * 取消静音倒计时
   */
  const cancelSilenceCountdown = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }

    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }

    silenceStartTimeRef.current = null;
    setState(prev => ({ ...prev, isSilent: false, silenceCountdown: 0 }));
  }, []);

  /**
   * 开始录音
   */
  const startRecording = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, error: null, transcript: '', volume: 0 }));
      accumulatedTextRef.current = '';
      currentSentenceRef.current = '';
      currentSentenceIdRef.current = '';

      // 请求麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      mediaStreamRef.current = stream;

      // 创建音频上下文
      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);

      // 创建音频处理器 (4096 是缓冲区大小)
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      // 建立 WebSocket 连接
      const wsUrl = apiUrl.replace(/^http/, 'ws') + '/api/v1/asr/ws';
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setState(prev => ({ ...prev, isRecording: true }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.event === 'transcription') {
            const text = data.text || '';
            const isFinal = data.is_final || false;
            const sentenceId = data.sentence_id || '';

            if (text) {
              // 检查是否是新句子
              if (sentenceId !== currentSentenceIdRef.current) {
                // 新句子开始，将之前的句子加入累积文本
                if (currentSentenceRef.current) {
                  accumulatedTextRef.current += currentSentenceRef.current;
                }
                currentSentenceIdRef.current = sentenceId;
                currentSentenceRef.current = '';
              }

              // 更新当前句子（text 是完整的当前句子，不是增量）
              currentSentenceRef.current = text;

              // 如果句子结束，累积到最终文本
              if (isFinal) {
                accumulatedTextRef.current += text;
                currentSentenceRef.current = '';
                currentSentenceIdRef.current = '';
              }

              // 更新显示：已完成的句子 + 当前正在识别的句子
              const displayText = accumulatedTextRef.current + currentSentenceRef.current;
              setState(prev => ({ ...prev, transcript: displayText }));

              if (onTranscript) {
                onTranscript(text, isFinal);
              }
            }

            // 收到文本说明有声音，取消静音倒计时
            cancelSilenceCountdown();

          } else if (data.event === 'complete') {
            console.log('Recognition completed');
          } else if (data.event === 'error') {
            const errorMsg = data.message || 'Recognition error';
            console.error('ASR error:', errorMsg);
            setState(prev => ({ ...prev, error: errorMsg }));
            if (onError) {
              onError(errorMsg);
            }
            stopRecording();
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setState(prev => ({ ...prev, error: 'WebSocket connection error' }));
        if (onError) {
          onError('WebSocket connection error');
        }
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
      };

      // 音频处理
      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);

        // 计算音量
        const rms = calculateRMS(inputData);
        setState(prev => ({ ...prev, volume: rms }));

        // 检测静音
        if (rms < silenceThreshold) {
          // 静音
          if (!silenceStartTimeRef.current) {
            startSilenceCountdown();
          }
        } else {
          // 有声音
          cancelSilenceCountdown();
        }

        // 转换为 PCM 16-bit
        const pcmData = floatTo16BitPCM(inputData);

        // 发送音频数据到后端
        if (ws.readyState === WebSocket.OPEN) {
          const base64Data = btoa(
            String.fromCharCode.apply(null, Array.from(new Uint8Array(pcmData.buffer)))
          );
          ws.send(JSON.stringify({
            type: 'audio',
            data: base64Data,
          }));
        }
      };

      // 连接音频节点
      source.connect(processor);
      processor.connect(audioContext.destination);

    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to start recording';
      console.error('Start recording error:', err);
      setState(prev => ({ ...prev, error: errorMsg }));
      if (onError) {
        onError(errorMsg);
      }
      cleanup();
    }
  }, [apiUrl, silenceThreshold, onTranscript, onError, startSilenceCountdown, cancelSilenceCountdown, cleanup]);

  /**
   * 停止录音
   */
  const stopRecording = useCallback(() => {
    cleanup();
    setState(prev => ({
      ...prev,
      isRecording: false,
      isSilent: false,
      silenceCountdown: 0,
      volume: 0,
    }));
  }, [cleanup]);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  return {
    ...state,
    startRecording,
    stopRecording,
  };
}
