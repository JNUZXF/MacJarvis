import React, { useState, useEffect } from 'react';
import type { TTSConfig, TTSVoice, TTSModel } from '../types';
import styles from './TTSSettings.module.css';

interface TTSSettingsProps {
  config: TTSConfig;
  apiUrl: string;
  onConfigChange: (config: Partial<TTSConfig>) => void;
}

export const TTSSettings: React.FC<TTSSettingsProps> = ({ config, apiUrl, onConfigChange }) => {
  const [voices, setVoices] = useState<TTSVoice[]>([]);
  const [models, setModels] = useState<TTSModel[]>([]);
  const [isLoadingVoices, setIsLoadingVoices] = useState(false);

  // 加载可用音色列表和模型列表
  useEffect(() => {
    const loadVoices = async () => {
      setIsLoadingVoices(true);
      try {
        const response = await fetch(`${apiUrl}/api/v1/tts/voices`);
        if (response.ok) {
          const data = await response.json();
          setVoices(data.voices || []);
          setModels(data.models || []);
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

  // 验证并修正配置：确保音色和模型匹配
  useEffect(() => {
    if (voices.length === 0 || models.length === 0) {
      return;
    }

    const currentVoice = voices.find(v => v.id === config.voice);
    const updates: Partial<TTSConfig> = {};

    // 如果当前音色不存在，使用第一个可用音色
    if (!currentVoice) {
      updates.voice = voices[0].id;
      if (voices[0].models && voices[0].models.length > 0) {
        updates.model = voices[0].models[0];
      }
    } else {
      // 如果当前音色不支持当前模型，自动切换模型或音色
      if (currentVoice.models && !currentVoice.models.includes(config.model)) {
        // 优先切换模型到音色支持的第一个模型
        if (currentVoice.models.length > 0) {
          updates.model = currentVoice.models[0];
        } else {
          // 如果音色没有支持的模型，切换到支持当前模型的第一个音色
          const compatibleVoice = voices.find(v => 
            v.models && v.models.includes(config.model)
          );
          if (compatibleVoice) {
            updates.voice = compatibleVoice.id;
          }
        }
      }
    }

    // 如果有更新，应用配置
    if (Object.keys(updates).length > 0) {
      onConfigChange(updates);
    }
  }, [voices, models, config.voice, config.model, onConfigChange]);

  // 获取当前音色支持的模型列表
  const getAvailableModels = (): TTSModel[] => {
    const currentVoice = voices.find(v => v.id === config.voice);
    if (!currentVoice || !currentVoice.models) {
      return models; // 如果没有限制，返回所有模型
    }
    return models.filter(m => currentVoice.models!.includes(m.id));
  };

  // 处理音色变更
  const handleVoiceChange = (voiceId: string) => {
    const selectedVoice = voices.find(v => v.id === voiceId);
    const updates: Partial<TTSConfig> = { voice: voiceId };
    
    // 如果选择的音色只支持特定模型，自动切换模型
    if (selectedVoice?.models && selectedVoice.models.length === 1) {
      updates.model = selectedVoice.models[0];
    }
    
    onConfigChange(updates);
  };

  // 处理模型变更
  const handleModelChange = (modelId: string) => {
    const currentVoice = voices.find(v => v.id === config.voice);
    const updates: Partial<TTSConfig> = { model: modelId };
    
    // 如果当前音色不支持新选择的模型，自动切换到一个支持该模型的音色
    if (currentVoice?.models && !currentVoice.models.includes(modelId)) {
      const compatibleVoice = voices.find(v => 
        v.models && v.models.includes(modelId)
      );
      if (compatibleVoice) {
        updates.voice = compatibleVoice.id;
      }
    }
    
    onConfigChange(updates);
  };

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
            <label className={styles.label}>模型选择</label>
            {isLoadingVoices ? (
              <p className={styles.loading}>加载中...</p>
            ) : (
              <select
                value={config.model}
                onChange={(e) => handleModelChange(e.target.value)}
                className={styles.select}
                disabled={getAvailableModels().length === 1}
              >
                {getAvailableModels().map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} - {model.description}
                  </option>
                ))}
              </select>
            )}
            {getAvailableModels().length === 1 && (
              <p className={styles.description}>
                当前音色仅支持此模型
              </p>
            )}
          </div>

          <div className={styles.settingRow}>
            <label className={styles.label}>音色选择</label>
            {isLoadingVoices ? (
              <p className={styles.loading}>加载中...</p>
            ) : (
              <select
                value={config.voice}
                onChange={(e) => handleVoiceChange(e.target.value)}
                className={styles.select}
              >
                {voices.map((voice) => (
                  <option key={voice.id} value={voice.id}>
                    {voice.name} ({voice.gender === 'male' ? '男' : '女'}声)
                    {voice.models && voice.models.length === 1 && ` - 仅${voice.models[0]}`}
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
