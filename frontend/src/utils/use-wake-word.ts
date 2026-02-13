import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useVoiceRecognition } from './use-voice-recognition';
import type { WakeWordConfig } from '../types';

interface UseWakeWordOptions {
  apiUrl: string;
  config: WakeWordConfig;
  onWakeWordDetected?: (wakeWord: string, sourceText: string) => void;
  onCommandDetected: (command: string, sourceText: string) => void;
  onError?: (error: string) => void;
}

type WakeWordState = 'disabled' | 'listening' | 'waiting_command' | 'cooldown';

function normalizeText(text: string): string {
  return text
    .toLowerCase()
    .replace(/[，。！？、,.!?;；:：]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function extractCommand(text: string, wakeWord: string, stripWakeWord: boolean): string {
  if (!stripWakeWord) {
    return text.trim();
  }

  const regex = new RegExp(escapeRegExp(wakeWord), 'i');
  const stripped = text.replace(regex, '').replace(/^[，。！？、,.!?;；:：\s]+/, '');
  return stripped.trim();
}

export function useWakeWord(options: UseWakeWordOptions) {
  const { apiUrl, config, onWakeWordDetected, onCommandDetected, onError } = options;
  const [wakeWordState, setWakeWordState] = useState<WakeWordState>('disabled');
  const [lastWakeWord, setLastWakeWord] = useState('');

  const waitingCommandRef = useRef(false);
  const commandTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const enabledRef = useRef(config.enabled);
  const recordingRef = useRef(false);
  const startRecordingRef = useRef<(() => Promise<void>) | null>(null);
  const stopRecordingRef = useRef<(() => void) | null>(null);

  const keywords = useMemo(
    () => config.keywords.map((k) => k.trim()).filter(Boolean),
    [config.keywords]
  );

  const clearTimers = useCallback(() => {
    if (commandTimerRef.current) {
      clearTimeout(commandTimerRef.current);
      commandTimerRef.current = null;
    }
    if (restartTimerRef.current) {
      clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
    }
  }, []);

  const scheduleRestart = useCallback(
    (delayMs: number) => {
      if (!enabledRef.current) {
        return;
      }
      if (restartTimerRef.current) {
        clearTimeout(restartTimerRef.current);
      }
      setWakeWordState('cooldown');
      restartTimerRef.current = setTimeout(() => {
        restartTimerRef.current = null;
        if (enabledRef.current && !recordingRef.current && startRecordingRef.current) {
          startRecordingRef.current().catch((err) => {
            const message = err instanceof Error ? err.message : String(err);
            if (onError) {
              onError(message);
            }
          });
        }
      }, Math.max(0, delayMs));
    },
    [onError]
  );

  const { isRecording, transcript, error, startRecording, stopRecording } = useVoiceRecognition({
    apiUrl,
    silenceThreshold: 0.01,
    silenceDuration: 1300,
    onComplete: (finalText) => {
      const trimmedText = finalText.trim();

      if (!trimmedText) {
        scheduleRestart(300);
        return;
      }

      if (waitingCommandRef.current) {
        waitingCommandRef.current = false;
        if (commandTimerRef.current) {
          clearTimeout(commandTimerRef.current);
          commandTimerRef.current = null;
        }
        setWakeWordState('cooldown');
        onCommandDetected(trimmedText, trimmedText);
        scheduleRestart(config.cooldownMs);
        return;
      }

      const normalized = normalizeText(trimmedText);
      const matchedKeyword = keywords.find((keyword) =>
        normalized.includes(normalizeText(keyword))
      );

      if (!matchedKeyword) {
        scheduleRestart(300);
        return;
      }

      setLastWakeWord(matchedKeyword);
      if (onWakeWordDetected) {
        onWakeWordDetected(matchedKeyword, trimmedText);
      }

      const command = extractCommand(trimmedText, matchedKeyword, config.stripWakeWord);
      if (command) {
        setWakeWordState('cooldown');
        onCommandDetected(command, trimmedText);
        scheduleRestart(config.cooldownMs);
        return;
      }

      waitingCommandRef.current = true;
      setWakeWordState('waiting_command');
      commandTimerRef.current = setTimeout(() => {
        waitingCommandRef.current = false;
        commandTimerRef.current = null;
        scheduleRestart(300);
      }, config.commandTimeoutMs);
      scheduleRestart(300);
    },
    onError: (message) => {
      if (onError) {
        onError(message);
      }
      scheduleRestart(1000);
    },
  });

  useEffect(() => {
    recordingRef.current = isRecording;
  }, [isRecording]);

  useEffect(() => {
    startRecordingRef.current = startRecording;
    stopRecordingRef.current = stopRecording;
  }, [startRecording, stopRecording]);

  useEffect(() => {
    enabledRef.current = config.enabled;
  }, [config.enabled]);

  useEffect(() => {
    if (!config.enabled) {
      clearTimers();
      waitingCommandRef.current = false;
      setWakeWordState('disabled');
      if (isRecording && stopRecordingRef.current) {
        stopRecordingRef.current();
      }
      return;
    }

    if (keywords.length === 0) {
      clearTimers();
      waitingCommandRef.current = false;
      setWakeWordState('disabled');
      if (isRecording && stopRecordingRef.current) {
        stopRecordingRef.current();
      }
      return;
    }

    if (!isRecording && startRecordingRef.current && !restartTimerRef.current) {
      setWakeWordState('listening');
      startRecordingRef.current().catch((err) => {
        const message = err instanceof Error ? err.message : String(err);
        if (onError) {
          onError(message);
        }
      });
    } else if (wakeWordState !== 'waiting_command') {
      setWakeWordState('listening');
    }

    return () => {
      clearTimers();
    };
  }, [
    clearTimers,
    config.enabled,
    keywords.length,
    isRecording,
    onError,
    wakeWordState,
  ]);

  useEffect(() => {
    return () => {
      clearTimers();
    };
  }, [clearTimers]);

  return {
    wakeWordState,
    lastWakeWord,
    isRecording,
    transcript,
    error,
  };
}
