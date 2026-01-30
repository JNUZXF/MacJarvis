"""
TTS (Text-to-Speech) API
支持流式文本转语音，使用通义千问 DashScope API
"""
import os
import base64
import asyncio
from typing import AsyncGenerator
from queue import Queue
from threading import Thread

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat, ResultCallback

router = APIRouter()

# 从环境变量获取 API Key
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("DASHSCOPE_API_KEY not found in environment variables")

dashscope.api_key = DASHSCOPE_API_KEY


class TTSRequest(BaseModel):
    """TTS 请求模型"""
    text: str
    model: str = "cosyvoice-v3-flash"
    voice: str = "longyingtao_v3"
    format: str = "pcm_22050hz_mono_16bit"


class StreamingCallback(ResultCallback):
    """流式音频回调处理器"""

    def __init__(self):
        super().__init__()
        self.audio_queue = Queue()
        self.is_completed = False
        self.error_message = None

    def on_open(self):
        """连接建立"""
        pass

    def on_complete(self):
        """合成完成"""
        self.is_completed = True
        self.audio_queue.put(None)  # 结束标记

    def on_error(self, message: str):
        """错误处理"""
        self.error_message = message
        self.audio_queue.put(None)

    def on_close(self):
        """连接关闭"""
        pass

    def on_event(self, message):
        """事件处理"""
        pass

    def on_data(self, data: bytes) -> None:
        """接收音频数据"""
        self.audio_queue.put(data)


async def synthesize_speech_stream(
    text: str,
    model: str = "cosyvoice-v3-flash",
    voice: str = "longyingtao_v3"
) -> AsyncGenerator[bytes, None]:
    """
    流式语音合成

    Args:
        text: 要合成的文本
        model: 模型名称
        voice: 音色

    Yields:
        音频数据块（bytes）
    """
    callback = StreamingCallback()

    # 创建合成器
    synthesizer = SpeechSynthesizer(
        model=model,
        voice=voice,
        format=AudioFormat.PCM_22050HZ_MONO_16BIT,
        callback=callback,
    )

    # 在单独的线程中进行合成（DashScope SDK 是同步的）
    def synthesize():
        try:
            synthesizer.streaming_call(text)
            synthesizer.streaming_complete()
        except Exception as e:
            callback.error_message = str(e)
            callback.audio_queue.put(None)

    thread = Thread(target=synthesize, daemon=True)
    thread.start()

    # 异步生成音频数据
    while True:
        # 使用 asyncio 避免阻塞
        audio_chunk = await asyncio.get_event_loop().run_in_executor(
            None, callback.audio_queue.get
        )

        if audio_chunk is None:
            # 检查是否有错误
            if callback.error_message:
                raise HTTPException(
                    status_code=500,
                    detail=f"TTS synthesis failed: {callback.error_message}"
                )
            break

        yield audio_chunk

    thread.join(timeout=1)


@router.post("/synthesize")
async def synthesize_speech(request: TTSRequest):
    """
    单次语音合成接口

    接收文本，返回完整的音频数据（base64 编码）
    """
    try:
        audio_data = b""
        async for chunk in synthesize_speech_stream(
            text=request.text,
            model=request.model,
            voice=request.voice
        ):
            audio_data += chunk

        # 返回 base64 编码的音频
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        return {
            "success": True,
            "audio": audio_base64,
            "format": "pcm_22050hz_mono_16bit",
            "sample_rate": 22050,
            "channels": 1,
            "sample_width": 2  # 16-bit = 2 bytes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synthesize-stream")
async def synthesize_speech_streaming(request: TTSRequest):
    """
    流式语音合成接口

    接收文本，以流式方式返回音频数据块
    """
    async def audio_generator():
        try:
            async for chunk in synthesize_speech_stream(
                text=request.text,
                model=request.model,
                voice=request.voice
            ):
                # 将音频数据编码为 base64 并返回
                chunk_base64 = base64.b64encode(chunk).decode('utf-8')
                yield f"data: {chunk_base64}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"

    return StreamingResponse(
        audio_generator(),
        media_type="text/event-stream"
    )


@router.get("/voices")
async def list_voices():
    """
    获取可用的音色列表

    返回所有支持的音色选项
    """
    voices = [
        {"id": "longyingtao_v3", "name": "龙吟桃", "language": "zh-CN", "gender": "female"},
        {"id": "zhichu_v3", "name": "知初", "language": "zh-CN", "gender": "female"},
        {"id": "zhitian_v3", "name": "知甜", "language": "zh-CN", "gender": "female"},
        {"id": "zhiyan_v3", "name": "知燕", "language": "zh-CN", "gender": "female"},
        {"id": "zhibei_v3", "name": "知贝", "language": "zh-CN", "gender": "female"},
        {"id": "zhimiao_v3", "name": "知妙", "language": "zh-CN", "gender": "female"},
        {"id": "zhishuo_v3", "name": "知硕", "language": "zh-CN", "gender": "male"},
        {"id": "zhiyu_v3", "name": "知语", "language": "zh-CN", "gender": "male"},
    ]
    return {"voices": voices}
