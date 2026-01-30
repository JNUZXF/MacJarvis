/**
 * TTS Manager
 * 负责流式文本的智能分段、音频合成和播放队列管理
 */

import type { TTSConfig } from '../types';

interface AudioQueueItem {
  id: string;
  text: string;
  audioData?: ArrayBuffer;
  status: 'pending' | 'loading' | 'ready' | 'playing' | 'completed' | 'failed';
  error?: string;
}

export class TTSManager {
  private config: TTSConfig;
  private apiUrl: string;
  private textBuffer: string = '';
  private audioQueue: AudioQueueItem[] = [];
  private currentAudioIndex: number = 0;
  private isPlaying: boolean = false;
  private audioContext: AudioContext | null = null;
  private currentSource: AudioBufferSourceNode | null = null;
  private nextSegmentId: number = 0;

  // 句子结束标点
  private static SENTENCE_ENDINGS = /[。！？；.!?;]/;
  // 次要分隔符
  private static SECONDARY_DELIMITERS = /[，、,]/;

  constructor(config: TTSConfig, apiUrl: string) {
    this.config = config;
    this.apiUrl = apiUrl;
  }

  /**
   * 添加文本片段并触发分段处理
   */
  addText(text: string): void {
    if (!this.config.enabled) {
      return;
    }

    this.textBuffer += text;
    this.processBuffer();
  }

  /**
   * 处理文本缓冲区，提取可发送的段落
   */
  private processBuffer(): void {
    while (true) {
      const segment = this.extractSegment();
      if (!segment) {
        break;
      }
      this.enqueueSegment(segment);
    }
  }

  /**
   * 从缓冲区提取一个段落
   */
  private extractSegment(): string | null {
    if (!this.textBuffer) {
      return null;
    }

    const bufferLength = this.textBuffer.length;

    // 缓冲区过长，强制分段
    if (bufferLength > this.config.maxSegmentLength) {
      return this.forceSplit();
    }

    // 缓冲区过短，等待更多文本
    if (bufferLength < this.config.minSegmentLength) {
      return null;
    }

    // 查找自然分段点
    return this.findNaturalBreak();
  }

  /**
   * 查找自然的分段点（句子结束标点）
   */
  private findNaturalBreak(): string | null {
    const matches = Array.from(this.textBuffer.matchAll(new RegExp(TTSManager.SENTENCE_ENDINGS, 'g')));

    if (matches.length === 0) {
      return null;
    }

    // 寻找最接近偏好长度的分段点
    let bestMatch: RegExpMatchArray | null = null;
    let bestDistance = Infinity;

    for (const match of matches) {
      const pos = (match.index ?? 0) + match[0].length;
      const distance = Math.abs(pos - this.config.preferSegmentLength);

      // 必须满足最小长度要求
      if (pos >= this.config.minSegmentLength && distance < bestDistance) {
        bestMatch = match;
        bestDistance = distance;
      }
    }

    if (bestMatch) {
      const pos = (bestMatch.index ?? 0) + bestMatch[0].length;
      const segment = this.textBuffer.slice(0, pos).trim();
      this.textBuffer = this.textBuffer.slice(pos).trim();
      return segment;
    }

    return null;
  }

  /**
   * 强制分段（当缓冲区过长时）
   */
  private forceSplit(): string {
    const maxPos = Math.min(this.textBuffer.length, this.config.maxSegmentLength);
    const searchText = this.textBuffer.slice(0, maxPos);

    // 尝试在次要分隔符处分段
    const matches = Array.from(searchText.matchAll(new RegExp(TTSManager.SECONDARY_DELIMITERS, 'g')));

    let pos: number;
    if (matches.length > 0) {
      // 取最后一个次要分隔符
      const lastMatch = matches[matches.length - 1];
      pos = (lastMatch.index ?? 0) + lastMatch[0].length;
    } else {
      // 没有次要分隔符，直接截断
      pos = maxPos;
    }

    const segment = this.textBuffer.slice(0, pos).trim();
    this.textBuffer = this.textBuffer.slice(pos).trim();
    return segment;
  }

  /**
   * 将段落加入队列并请求音频合成
   */
  private enqueueSegment(text: string): void {
    const id = `segment-${this.nextSegmentId++}`;
    const item: AudioQueueItem = {
      id,
      text,
      status: 'pending',
    };

    this.audioQueue.push(item);
    this.synthesizeAudio(item);

    // 如果没有正在播放，启动播放
    if (!this.isPlaying) {
      this.playNext();
    }
  }

  /**
   * 合成音频
   */
  private async synthesizeAudio(item: AudioQueueItem): Promise<void> {
    item.status = 'loading';

    try {
      const response = await fetch(`${this.apiUrl}/api/v1/tts/synthesize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: item.text,
          model: this.config.model,
          voice: this.config.voice,
        }),
      });

      if (!response.ok) {
        throw new Error(`TTS API error: ${response.status}`);
      }

      const data = await response.json();

      // 解码 base64 音频数据
      const audioBase64 = data.audio;
      const binaryString = atob(audioBase64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      item.audioData = bytes.buffer;
      item.status = 'ready';

      // 如果这是下一个要播放的，立即播放
      if (this.audioQueue[this.currentAudioIndex] === item && !this.isPlaying) {
        this.playNext();
      }
    } catch (error) {
      console.error('TTS synthesis failed:', error);
      item.status = 'failed';
      item.error = error instanceof Error ? error.message : 'Unknown error';

      // 跳过失败的片段
      if (this.audioQueue[this.currentAudioIndex] === item) {
        this.playNext();
      }
    }
  }

  /**
   * 播放下一个音频片段
   */
  private async playNext(): Promise<void> {
    if (this.currentAudioIndex >= this.audioQueue.length) {
      this.isPlaying = false;
      return;
    }

    const item = this.audioQueue[this.currentAudioIndex];

    // 等待音频数据准备好
    if (item.status === 'pending' || item.status === 'loading') {
      // 等待一段时间后重试
      setTimeout(() => this.playNext(), 100);
      return;
    }

    // 跳过失败的片段
    if (item.status === 'failed') {
      this.currentAudioIndex++;
      this.playNext();
      return;
    }

    // 播放音频
    if (item.status === 'ready' && item.audioData) {
      await this.playAudio(item);
    }
  }

  /**
   * 播放音频数据
   */
  private async playAudio(item: AudioQueueItem): Promise<void> {
    if (!item.audioData) {
      return;
    }

    this.isPlaying = true;
    item.status = 'playing';

    try {
      // 初始化 AudioContext
      if (!this.audioContext) {
        this.audioContext = new AudioContext();
      }

      // 确保 AudioContext 已启动
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      // 解码音频数据（PCM 16-bit 单声道 22050Hz）
      const audioBuffer = await this.decodePCM(item.audioData, 22050, 1);

      // 创建音频源
      this.currentSource = this.audioContext.createBufferSource();
      this.currentSource.buffer = audioBuffer;
      this.currentSource.connect(this.audioContext.destination);

      // 播放结束后播放下一个
      this.currentSource.onended = () => {
        item.status = 'completed';
        this.currentAudioIndex++;
        this.isPlaying = false;
        this.playNext();
      };

      this.currentSource.start();
    } catch (error) {
      console.error('Audio playback failed:', error);
      item.status = 'failed';
      item.error = error instanceof Error ? error.message : 'Unknown error';
      this.currentAudioIndex++;
      this.isPlaying = false;
      this.playNext();
    }
  }

  /**
   * 解码 PCM 音频数据
   */
  private async decodePCM(
    arrayBuffer: ArrayBuffer,
    sampleRate: number,
    channels: number
  ): Promise<AudioBuffer> {
    if (!this.audioContext) {
      throw new Error('AudioContext not initialized');
    }

    // PCM 16-bit 数据
    const dataView = new DataView(arrayBuffer);
    const samples = new Float32Array(arrayBuffer.byteLength / 2);

    // 转换为 Float32
    for (let i = 0; i < samples.length; i++) {
      const int16 = dataView.getInt16(i * 2, true); // little-endian
      samples[i] = int16 / 32768.0; // 归一化到 [-1, 1]
    }

    // 创建 AudioBuffer
    const audioBuffer = this.audioContext.createBuffer(channels, samples.length, sampleRate);
    audioBuffer.copyToChannel(samples, 0);

    return audioBuffer;
  }

  /**
   * 刷新缓冲区，处理剩余文本
   */
  flush(): void {
    if (this.textBuffer.trim()) {
      this.enqueueSegment(this.textBuffer.trim());
      this.textBuffer = '';
    }
  }

  /**
   * 停止播放
   */
  stop(): void {
    if (this.currentSource) {
      this.currentSource.stop();
      this.currentSource = null;
    }
    this.isPlaying = false;
  }

  /**
   * 清空队列和缓冲区
   */
  clear(): void {
    this.stop();
    this.textBuffer = '';
    this.audioQueue = [];
    this.currentAudioIndex = 0;
    this.nextSegmentId = 0;
  }

  /**
   * 更新配置
   */
  updateConfig(config: Partial<TTSConfig>): void {
    this.config = { ...this.config, ...config };

    // 如果禁用了 TTS，清空队列
    if (!this.config.enabled) {
      this.clear();
    }
  }

  /**
   * 获取队列状态
   */
  getStatus() {
    return {
      bufferLength: this.textBuffer.length,
      queueLength: this.audioQueue.length,
      currentIndex: this.currentAudioIndex,
      isPlaying: this.isPlaying,
      queue: this.audioQueue.map(item => ({
        id: item.id,
        text: item.text.slice(0, 50) + (item.text.length > 50 ? '...' : ''),
        status: item.status,
      })),
    };
  }
}
