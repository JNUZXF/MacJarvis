# File: backend/app/api/schemas/chat.py
# Purpose: Pydantic schemas for chat-related API endpoints
from pydantic import BaseModel, Field
from typing import Optional, List


class ChatAttachment(BaseModel):
    """File attachment for chat message"""
    file_id: str = Field(..., description="Unique file identifier")
    filename: Optional[str] = Field(None, description="Original filename")
    content_type: Optional[str] = Field(None, description="MIME type")
    path: Optional[str] = Field(None, description="File path (internal use)")


class ChatRequest(BaseModel):
    """Request schema for chat endpoint"""
    message: str = Field(..., min_length=1, description="User message")
    model: Optional[str] = Field(None, description="Model to use (optional)")
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    attachments: Optional[List[ChatAttachment]] = Field(
        None,
        description="Optional file attachments"
    )
    stream: bool = Field(True, description="Whether to stream response")
    
    # TTS配置字段
    tts_enabled: bool = Field(False, description="是否启用TTS语音合成")
    tts_voice: str = Field("longyingtao_v3", description="TTS音色")
    tts_model: str = Field("cosyvoice-v3-flash", description="TTS模型")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "帮我列出当前目录的文件",
                "user_id": "user123",
                "session_id": "session456",
                "model": "gpt-4o-mini",
                "stream": True,
                "tts_enabled": False,
                "tts_voice": "longyingtao_v3",
                "tts_model": "cosyvoice-v3-flash"
            }
        }


class ChatResponse(BaseModel):
    """Response schema for non-streaming chat"""
    content: str = Field(..., description="Assistant response")
    model: str = Field(..., description="Model used")
    session_id: str = Field(..., description="Session identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "当前目录包含以下文件：...",
                "model": "gpt-4o-mini",
                "session_id": "session456"
            }
        }
