/**
 * TTS Player
 * 负责接收后端推送的音频数据并进行无缝播放
 * 分段逻辑已移至后端处理
 */

import type { TTSConfig } from '../types';

interface AudioSegment {
  segmentId: number;
  text: string;
  audioChunks: ArrayBuffer[];
  audioBuffer?: AudioBuffer;
  status: 'receiving' | 'ready' | 'playing' | 'completed' | 'failed';
  error?: string;
}

export class TTSPlayer {
  private config: TTSConfig;
  private audioSegments: Map<number, AudioSegment> = new Map();
  private segmentOrder: number[] = [];
  private currentSegmentIndex: number = 0;
  private isPlaying: boolean = false;
  private audioContext: AudioContext | null = null;
  private currentSource: AudioBufferSourceNode | null = null;
  private nextSource: AudioBufferSourceNode | null = null;

  constructor(config: TTSConfig) {
    this.config = config;
  }

  /**
   * 开始新的音频段落
   */
  startSegment(segmentId: number, text: string): void {
    if (!this.config.enabled) {
      return;
    }

    const segment: AudioSegment = {
      segmentId,
      text,
      audioChunks: [],
      status: 'receiving',
    };

    this.audioSegments.set(segmentId, segment);
    this.segmentOrder.push(segmentId);

    console.log(`[TTS] 开始接收段落 ${segmentId}: ${text.slice(0, 30)}...`);
  }

  /**
   * 添加音频数据块
   */
  addAudioChunk(segmentId: number, audioChunk: string): void {
    if (!this.config.enabled) {
      return;
    }

    const segment = this.audioSegments.get(segmentId);
    if (!segment) {
      console.warn(`[TTS] 未找到段落 ${segmentId}`);
      return;
    }

    // 解码 base64 音频数据
    try {
      const binaryString = atob(audioChunk);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      segment.audioChunks.push(bytes.buffer);
    } catch (error) {
      console.error(`[TTS] 解码音频数据失败:`, error);
    }
  }

  /**
   * 标记段落完成
   */
  async segmentComplete(segmentId: number): Promise<void> {
    if (!this.config.enabled) {
      return;
    }

    const segment = this.audioSegments.get(segmentId);
    if (!segment) {
      console.warn(`[TTS] 未找到段落 ${segmentId}`);
      return;
    }

    // 合并所有音频块
    const totalLength = segment.audioChunks.reduce((sum, chunk) => sum + chunk.byteLength, 0);
    const mergedAudio = new Uint8Array(totalLength);
    let offset = 0;
    for (const chunk of segment.audioChunks) {
      mergedAudio.set(new Uint8Array(chunk), offset);
      offset += chunk.byteLength;
    }

    // 解码为 AudioBuffer
    try {
      const audioBuffer = await this.decodePCM(mergedAudio.buffer, 22050, 1);
      segment.audioBuffer = audioBuffer;
      segment.status = 'ready';

      console.log(`[TTS] 段落 ${segmentId} 准备完成，时长: ${audioBuffer.duration.toFixed(2)}s`);

      // 如果这是下一个要播放的段落且当前没有播放，启动播放
      if (this.segmentOrder[this.currentSegmentIndex] === segmentId && !this.isPlaying) {
        this.playNext();
      }
    } catch (error) {
      console.error(`[TTS] 解码音频失败:`, error);
      segment.status = 'failed';
      segment.error = error instanceof Error ? error.message : 'Unknown error';

      // 跳过失败的段落
      if (this.segmentOrder[this.currentSegmentIndex] === segmentId) {
        this.currentSegmentIndex++;
        this.playNext();
      }
    }
  }

  /**
   * 播放下一个音频段落
   */
  private async playNext(): Promise<void> {
    if (this.currentSegmentIndex >= this.segmentOrder.length) {
      this.isPlaying = false;
      console.log('[TTS] 所有段落播放完成');
      return;
    }

    const segmentId = this.segmentOrder[this.currentSegmentIndex];
    const segment = this.audioSegments.get(segmentId);

    if (!segment) {
      console.warn(`[TTS] 段落 ${segmentId} 不存在`);
      this.currentSegmentIndex++;
      this.playNext();
      return;
    }

    // 等待音频准备好
    if (segment.status === 'receiving') {
      // 等待一段时间后重试
      setTimeout(() => this.playNext(), 100);
      return;
    }

    // 跳过失败的段落
    if (segment.status === 'failed') {
      console.warn(`[TTS] 跳过失败的段落 ${segmentId}`);
      this.currentSegmentIndex++;
      this.playNext();
      return;
    }

    // 播放音频
    if (segment.status === 'ready' && segment.audioBuffer) {
      await this.playAudio(segment);
    }
  }

  /**
   * 播放音频数据（支持无缝衔接）
   */
  private async playAudio(segment: AudioSegment): Promise<void> {
    if (!segment.audioBuffer) {
      return;
    }

    this.isPlaying = true;
    segment.status = 'playing';

    try {
      // 初始化 AudioContext
      if (!this.audioContext) {
        this.audioContext = new AudioContext();
      }

      // 确保 AudioContext 已启动
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      // 创建音频源
      this.currentSource = this.audioContext.createBufferSource();
      this.currentSource.buffer = segment.audioBuffer;
      this.currentSource.connect(this.audioContext.destination);

      // 计算播放结束时间
      const currentTime = this.audioContext.currentTime;
      const duration = segment.audioBuffer.duration;
      const endTime = currentTime + duration;

      // 预调度下一个段落（无缝衔接）
      this.scheduleNextSegment(endTime);

      // 播放结束后播放下一个
      this.currentSource.onended = () => {
        segment.status = 'completed';
        this.currentSegmentIndex++;
        this.isPlaying = false;
        
        // 如果下一个段落没有被预调度（可能还未准备好），手动触发
        if (!this.nextSource) {
          this.playNext();
        }
      };

      this.currentSource.start(currentTime);

      console.log(`[TTS] 播放段落 ${segment.segmentId}, 时长: ${duration.toFixed(2)}s, 结束时间: ${endTime.toFixed(2)}s`);
    } catch (error) {
      console.error('[TTS] 音频播放失败:', error);
      segment.status = 'failed';
      segment.error = error instanceof Error ? error.message : 'Unknown error';
      this.currentSegmentIndex++;
      this.isPlaying = false;
      this.playNext();
    }
  }

  /**
   * 预调度下一个段落（实现无缝播放）
   */
  private scheduleNextSegment(startTime: number): void {
    const nextIndex = this.currentSegmentIndex + 1;
    if (nextIndex >= this.segmentOrder.length) {
      return;
    }

    const nextSegmentId = this.segmentOrder[nextIndex];
    const nextSegment = this.audioSegments.get(nextSegmentId);

    if (!nextSegment || nextSegment.status !== 'ready' || !nextSegment.audioBuffer) {
      console.log(`[TTS] 段落 ${nextSegmentId} 尚未准备好，无法预调度`);
      return;
    }

    if (!this.audioContext) {
      return;
    }

    try {
      // 创建下一个音频源
      this.nextSource = this.audioContext.createBufferSource();
      this.nextSource.buffer = nextSegment.audioBuffer;
      this.nextSource.connect(this.audioContext.destination);

      // 精确调度：在当前音频结束时立即开始
      this.nextSource.start(startTime);

      nextSegment.status = 'playing';

      // 播放结束后继续下一个
      this.nextSource.onended = () => {
        nextSegment.status = 'completed';
        this.currentSegmentIndex++;
        this.currentSource = this.nextSource;
        this.nextSource = null;
        this.isPlaying = false;
        
        // 继续播放后续段落
        this.playNext();
      };

      console.log(`[TTS] 预调度段落 ${nextSegmentId}, 将在 ${startTime.toFixed(2)}s 开始播放`);
    } catch (error) {
      console.error('[TTS] 预调度失败:', error);
      // 预调度失败不影响当前播放，会在当前结束后手动触发
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
      this.audioContext = new AudioContext();
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
   * 停止播放
   */
  stop(): void {
    if (this.currentSource) {
      try {
        this.currentSource.stop();
      } catch (e) {
        // 忽略已停止的错误
      }
      this.currentSource = null;
    }
    if (this.nextSource) {
      try {
        this.nextSource.stop();
      } catch (e) {
        // 忽略已停止的错误
      }
      this.nextSource = null;
    }
    this.isPlaying = false;
    console.log('[TTS] 停止播放');
  }

  /**
   * 清空所有数据
   */
  clear(): void {
    this.stop();
    this.audioSegments.clear();
    this.segmentOrder = [];
    this.currentSegmentIndex = 0;
    console.log('[TTS] 清空所有数据');
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
   * 获取播放状态
   */
  getStatus() {
    return {
      segmentCount: this.audioSegments.size,
      currentIndex: this.currentSegmentIndex,
      isPlaying: this.isPlaying,
      segments: Array.from(this.audioSegments.values()).map(seg => ({
        segmentId: seg.segmentId,
        text: seg.text.slice(0, 50) + (seg.text.length > 50 ? '...' : ''),
        status: seg.status,
        chunksReceived: seg.audioChunks.length,
      })),
    };
  }
}
