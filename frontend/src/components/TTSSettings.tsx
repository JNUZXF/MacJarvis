import React, { useState, useEffect } from 'react';
import type { TTSConfig, TTSVoice } from '../types';
import styles from './TTSSettings.module.css';

interface TTSSettingsProps {
  config: TTSConfig;
  apiUrl: string;
  onConfigChange: (config: Partial<TTSConfig>) => void;
}

export const TTSSettings: React.FC<TTSSettingsProps> = ({ config, apiUrl, onConfigChange }) => {
  const [voices, setVoices] = useState<TTSVoice[]>([]);
  const [isLoadingVoices, setIsLoadingVoices] = useState(false);

  // 加载可用音色列表
  useEffect(() => {
    const loadVoices = async () => {
      setIsLoadingVoices(true);
      try {
        const response = await fetch(`${apiUrl}/api/v1/tts/voices`);
        if (response.ok) {
          const data = await response.json();
          setVoices(data.voices || []);
        }
      } catch (error) {
        console.error('Failed to load TTS voices:', error);
      } finally {
        setIsLoadingVoices(false);
      }
    };

    if (config.enabled) {
      loadVoices();
    }
  }, [apiUrl, config.enabled]);

  return (
    <div className={styles.ttsSettings}>
      <h3 className={styles.sectionTitle}>语音合成 (TTS)</h3>

      {/* TTS 开关 */}
      <div className={styles.settingRow}>
        <label className={styles.switchLabel}>
          <input
            type="checkbox"
            checked={config.enabled}
            onChange={(e) => onConfigChange({ enabled: e.target.checked })}
            className={styles.switchInput}
          />
          <span className={styles.switchSlider}></span>
          <span className={styles.switchText}>启用语音播放</span>
        </label>
        <p className={styles.description}>智能体回复时自动播放语音</p>
      </div>

      {/* 音色选择 */}
      {config.enabled && (
        <>
          <div className={styles.settingRow}>
            <label className={styles.label}>音色选择</label>
            {isLoadingVoices ? (
              <p className={styles.loading}>加载中...</p>
            ) : (
              <select
                value={config.voice}
                onChange={(e) => onConfigChange({ voice: e.target.value })}
                className={styles.select}
              >
                {voices.map((voice) => (
                  <option key={voice.id} value={voice.id}>
                    {voice.name} ({voice.gender === 'male' ? '男' : '女'}声)
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* 高级设置 */}
          <details className={styles.advancedSettings}>
            <summary className={styles.advancedSummary}>高级设置</summary>

            <div className={styles.settingRow}>
              <label className={styles.label}>
                最小段落长度
                <span className={styles.labelValue}>{config.minSegmentLength} 字符</span>
              </label>
              <input
                type="range"
                min="5"
                max="50"
                value={config.minSegmentLength}
                onChange={(e) => onConfigChange({ minSegmentLength: parseInt(e.target.value) })}
                className={styles.slider}
              />
              <p className={styles.description}>低于此长度会累积后再播放</p>
            </div>

            <div className={styles.settingRow}>
              <label className={styles.label}>
                最大段落长度
                <span className={styles.labelValue}>{config.maxSegmentLength} 字符</span>
              </label>
              <input
                type="range"
                min="100"
                max="500"
                value={config.maxSegmentLength}
                onChange={(e) => onConfigChange({ maxSegmentLength: parseInt(e.target.value) })}
                className={styles.slider}
              />
              <p className={styles.description}>超过此长度会强制分段</p>
            </div>

            <div className={styles.settingRow}>
              <label className={styles.label}>
                偏好段落长度
                <span className={styles.labelValue}>{config.preferSegmentLength} 字符</span>
              </label>
              <input
                type="range"
                min="20"
                max="200"
                value={config.preferSegmentLength}
                onChange={(e) => onConfigChange({ preferSegmentLength: parseInt(e.target.value) })}
                className={styles.slider}
              />
              <p className={styles.description}>在合适的标点处尽量接近此长度分段</p>
            </div>
          </details>
        </>
      )}
    </div>
  );
};
