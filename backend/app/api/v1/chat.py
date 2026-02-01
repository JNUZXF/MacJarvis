# File: backend/app/api/v1/chat.py
# Purpose: Chat API endpoints with SSE streaming using Mac Agent Service
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncIterator
import json
import structlog

from app.api.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.user_service import UserService
from app.dependencies import get_chat_service, get_user_service
from app.core.tools.validators import set_runtime_allowed_roots, reset_runtime_allowed_roots

# Import Mac Agent Service
from agent.api_service import get_mac_agent_service

logger = structlog.get_logger(__name__)
router = APIRouter()


def add_sse_headers(response: StreamingResponse) -> StreamingResponse:
    """Add SSE headers to response"""
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@router.post("/chat", response_class=StreamingResponse)
async def chat_endpoint(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Chat endpoint with Server-Sent Events (SSE) streaming.
    
    Supports:
    - Streaming LLM responses
    - Tool execution
    - File attachments
    - Memory integration
    """
    
    async def event_generator() -> AsyncIterator[str]:
        """Generate SSE events"""
        # Send initial ping to establish connection
        yield ": ping\n\n"
        
        # Get user's allowed paths
        user_paths = await user_service.get_effective_allowed_roots(request.user_id)
        
        # Set runtime allowed roots for this request
        token = set_runtime_allowed_roots(user_paths)
        
        try:
            # Process chat message
            async for event in chat_service.process_chat_message(
                user_id=request.user_id,
                session_id=request.session_id,
                message=request.message,
                model=request.model,
                attachments=[att.model_dump() for att in (request.attachments or [])],
                stream=request.stream,
                tts_enabled=request.tts_enabled,
                tts_voice=request.tts_voice,
                tts_model=request.tts_model
            ):
                event_type = event.get("type")
                
                if event_type == "content":
                    content = event.get("content", "")
                    yield f"event: content\ndata: {json.dumps(content)}\n\n"
                
                elif event_type == "tool_start":
                    data = {
                        "name": event.get("name"),
                        "args": event.get("args"),
                        "tool_call_id": event.get("tool_call_id")
                    }
                    yield f"event: tool_start\ndata: {json.dumps(data)}\n\n"
                
                elif event_type == "tool_result":
                    data = {
                        "result": event.get("result"),
                        "tool_call_id": event.get("tool_call_id")
                    }
                    yield f"event: tool_result\ndata: {json.dumps(data, default=str)}\n\n"
                
                elif event_type == "tts_segment_start":
                    data = {
                        "segment_id": event.get("segment_id"),
                        "text": event.get("text")
                    }
                    yield f"event: tts_segment_start\ndata: {json.dumps(data)}\n\n"
                
                elif event_type == "tts_audio":
                    data = {
                        "segment_id": event.get("segment_id"),
                        "audio_chunk": event.get("audio_chunk"),
                        "is_final": event.get("is_final")
                    }
                    yield f"event: tts_audio\ndata: {json.dumps(data)}\n\n"
                
                elif event_type == "tts_segment_end":
                    data = {
                        "segment_id": event.get("segment_id")
                    }
                    yield f"event: tts_segment_end\ndata: {json.dumps(data)}\n\n"
                
                elif event_type == "tts_error":
                    data = {
                        "segment_id": event.get("segment_id"),
                        "error": event.get("error")
                    }
                    yield f"event: tts_error\ndata: {json.dumps(data)}\n\n"
                
                elif event_type == "error":
                    error_msg = event.get("error", "Unknown error")
                    yield f"event: error\ndata: {json.dumps(error_msg)}\n\n"
        
        except Exception as e:
            logger.error(
                "chat_stream_error",
                user_id=request.user_id,
                session_id=request.session_id,
                error=str(e)
            )
            yield f"event: error\ndata: {json.dumps(str(e))}\n\n"
        
        finally:
            # Reset runtime allowed roots
            try:
                reset_runtime_allowed_roots(token)
            except ValueError:
                # Context var reset failed (can happen in tests)
                pass
    
    return add_sse_headers(
        StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )
    )
