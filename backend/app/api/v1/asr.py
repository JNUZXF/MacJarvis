"""
File: backend/app/api/v1/asr.py
Path: backend/app/api/v1/asr.py
Purpose: 实时语音识别 WebSocket API，使用 DashScope paraformer-realtime-v2 模型
"""
import os
import base64
import asyncio
import json
from queue import Queue, Empty
from threading import Thread
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
import structlog

from app.config import get_settings

router = APIRouter()
logger = structlog.get_logger(__name__)

# 音频配置参数
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT_PCM = 'pcm'
BLOCK_SIZE = 3200


def get_dashscope_api_key() -> str:
    """获取 DashScope API Key"""
    settings = get_settings()
    api_key = settings.DASHSCOPE_API_KEY
    
    if not api_key:
        api_key = os.getenv("DASHSCOPE_API_KEY")
    
    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY not found. Please set it in .env file or environment variables.")
    return api_key


def init_dashscope():
    """初始化 DashScope API Key"""
    if not dashscope.api_key:
        dashscope.api_key = get_dashscope_api_key()


class WebSocketCallback(RecognitionCallback):
    """WebSocket 实时识别回调处理器"""

    def __init__(self, websocket: WebSocket):
        super().__init__()
        self.websocket = websocket
        self.message_queue = Queue()
        self.is_completed = False
        self.error_message: Optional[str] = None

    def on_open(self) -> None:
        """连接建立"""
        logger.info("asr_connection_opened")
        self.message_queue.put({
            "event": "open",
            "message": "Recognition started"
        })

    def on_close(self) -> None:
        """连接关闭"""
        logger.info("asr_connection_closed")
        self.message_queue.put({
            "event": "close",
            "message": "Recognition closed"
        })

    def on_complete(self) -> None:
        """识别完成"""
        logger.info("asr_recognition_completed")
        self.is_completed = True
        self.message_queue.put({
            "event": "complete",
            "message": "Recognition completed"
        })

    def on_error(self, message) -> None:
        """错误处理"""
        logger.error("asr_recognition_error", error=message)
        self.error_message = str(message)
        self.message_queue.put({
            "event": "error",
            "message": str(message)
        })

    def on_event(self, result: RecognitionResult) -> None:
        """识别事件处理"""
        try:
            sentence = result.get_sentence()
            if 'text' in sentence:
                text = sentence['text']
                is_final = RecognitionResult.is_sentence_end(sentence)
                
                # 获取句子的唯一标识（begin_time 可以作为句子ID）
                begin_time = sentence.get('begin_time', 0)
                
                logger.debug(
                    "asr_text_received",
                    text=text,
                    is_final=is_final,
                    begin_time=begin_time,
                    request_id=result.get_request_id()
                )
                
                # 将识别结果放入队列
                # text 是当前句子的完整文本，不是增量
                self.message_queue.put({
                    "event": "transcription",
                    "text": text,
                    "is_final": is_final,
                    "sentence_id": str(begin_time),  # 句子唯一标识
                    "request_id": result.get_request_id()
                })
                
                if is_final:
                    usage = result.get_usage(sentence)
                    logger.info(
                        "asr_sentence_completed",
                        request_id=result.get_request_id(),
                        usage=usage
                    )
        except Exception as e:
            logger.error("asr_event_processing_error", error=str(e))
            self.message_queue.put({
                "event": "error",
                "message": f"Event processing error: {str(e)}"
            })


@router.websocket("/ws")
async def asr_websocket_endpoint(websocket: WebSocket):
    """
    实时语音识别 WebSocket 端点
    
    接收前端发送的音频数据，调用 DashScope API 进行实时识别，
    并将识别结果推送回前端。
    
    消息协议:
    - 前端 -> 后端: {"type": "audio", "data": "base64_encoded_pcm_data"}
    - 前端 -> 后端: {"type": "stop"}
    - 后端 -> 前端: {"event": "transcription", "text": "...", "is_final": false}
    - 后端 -> 前端: {"event": "complete", "message": "..."}
    - 后端 -> 前端: {"event": "error", "message": "..."}
    """
    await websocket.accept()
    logger.info("websocket_connection_accepted", client=websocket.client)
    
    recognition = None
    callback = None
    message_sender_task = None
    
    try:
        # 初始化 DashScope
        init_dashscope()
        
        # 创建回调处理器
        callback = WebSocketCallback(websocket)
        
        # 创建识别实例
        recognition = Recognition(
            model='paraformer-realtime-v2',
            format=FORMAT_PCM,
            sample_rate=SAMPLE_RATE,
            semantic_punctuation_enabled=False,
            callback=callback
        )
        
        # 启动识别
        recognition.start()
        logger.info("asr_recognition_started")
        
        # 启动消息发送任务
        async def send_messages():
            """从队列中读取消息并发送到 WebSocket"""
            while True:
                try:
                    # 非阻塞方式获取消息
                    message = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: callback.message_queue.get(timeout=0.1)
                    )
                    
                    # 发送消息到前端
                    await websocket.send_json(message)
                    
                    # 如果是完成或错误消息，退出循环
                    if message.get("event") in ["complete", "error"]:
                        break
                        
                except Empty:
                    # 队列为空，继续等待
                    continue
                except Exception as e:
                    logger.error("message_send_error", error=str(e))
                    break
        
        message_sender_task = asyncio.create_task(send_messages())
        
        # 接收音频数据
        while True:
            try:
                # 接收 WebSocket 消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                msg_type = message.get("type")
                
                if msg_type == "audio":
                    # 解码音频数据
                    audio_data = base64.b64decode(message.get("data", ""))
                    
                    # 发送音频帧到识别服务
                    if recognition and audio_data:
                        recognition.send_audio_frame(audio_data)
                        
                elif msg_type == "stop":
                    # 停止识别
                    logger.info("asr_stop_requested")
                    break
                    
            except WebSocketDisconnect:
                logger.info("websocket_disconnected")
                break
            except json.JSONDecodeError as e:
                logger.error("invalid_json_message", error=str(e))
                await websocket.send_json({
                    "event": "error",
                    "message": "Invalid JSON message"
                })
            except Exception as e:
                logger.error("websocket_receive_error", error=str(e))
                await websocket.send_json({
                    "event": "error",
                    "message": str(e)
                })
                break
                
    except Exception as e:
        logger.error("asr_websocket_error", error=str(e), error_type=type(e).__name__)
        try:
            await websocket.send_json({
                "event": "error",
                "message": f"ASR service error: {str(e)}"
            })
        except:
            pass
            
    finally:
        # 清理资源
        if recognition:
            try:
                recognition.stop()
                logger.info("asr_recognition_stopped")
            except Exception as e:
                logger.error("asr_stop_error", error=str(e))
        
        if message_sender_task:
            message_sender_task.cancel()
            try:
                await message_sender_task
            except asyncio.CancelledError:
                pass
        
        try:
            await websocket.close()
        except:
            pass
        
        logger.info("websocket_connection_closed")


@router.get("/health")
async def asr_health_check():
    """ASR 服务健康检查"""
    try:
        # 检查 DashScope API Key 是否配置
        api_key = get_dashscope_api_key()
        
        return {
            "status": "healthy",
            "service": "asr",
            "api_configured": bool(api_key)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "asr",
            "error": str(e)
        }
