# File: backend/app/api/v1/memories.py
# Purpose: Simplified API endpoints for memory management
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
import json
import structlog

from app.services.memory_manager import MemoryManager
from app.infrastructure.database.connection import get_db_session
from app.dependencies import (
    get_llm_service,
    get_session_service,
    get_conversation_history_service,
    get_app_settings,
)
from app.services.llm_service import LLMService
from app.services.session_service import SessionService
from app.services.conversation_history_service import ConversationHistoryService
from app.config import Settings
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/memories", tags=["memories"])


@router.get("/{user_id}")
async def get_user_memories(
    user_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, str]:
    """
    Get all memory types for a user

    Args:
        user_id: User identifier
        db: Database session

    Returns:
        Dictionary with 5 memory types
    """
    try:
        memory_manager = MemoryManager(db)
        memories = await memory_manager.get_user_memory(user_id)
        return memories

    except Exception as e:
        logger.error("get_user_memories_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/refresh")
async def refresh_user_memory(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
    llm_service: LLMService = Depends(get_llm_service),
    session_service: SessionService = Depends(get_session_service),
    conversation_history_service: ConversationHistoryService = Depends(get_conversation_history_service),
    settings: Settings = Depends(get_app_settings),
) -> Dict[str, str]:
    """
    Manually trigger memory refresh for a user
    
    This endpoint calls LLM to summarize all user conversations
    and update memories by type.
    
    Args:
        user_id: User identifier
        db: Database session

    Returns:
        Updated memories
    """
    try:
        memory_manager = MemoryManager(db)

        sessions = await session_service.list_sessions(user_id=user_id, limit=200, offset=0)
        if not sessions:
            memories = await memory_manager.get_user_memory(user_id)
            logger.info("memory_refresh_no_sessions", user_id=user_id)
            return memories

        conversation_blocks = []
        for session in sessions:
            session_id = session.get("id")
            session_title = session.get("title") or "未命名会话"
            messages = await conversation_history_service.get_session_messages(
                session_id=session_id,
                include_system=False
            )
            if not messages:
                continue

            lines = [f"会话标题: {session_title}"]
            for msg in messages:
                role = msg.get("role")
                content = (msg.get("content") or "").strip()
                if not content:
                    continue
                if role == "user":
                    lines.append(f"用户: {content}")
                elif role == "assistant":
                    lines.append(f"助手: {content}")
            if len(lines) > 1:
                conversation_blocks.append("\n".join(lines))

        if not conversation_blocks:
            memories = await memory_manager.get_user_memory(user_id)
            logger.info("memory_refresh_no_messages", user_id=user_id)
            return memories

        full_text = "\n\n---\n\n".join(conversation_blocks)

        system_prompt = (
            "你是一个记忆整理助手。请根据用户所有对话内容，提炼并总结用户记忆。"
            "你必须只输出严格JSON，不要输出额外文字。"
            "JSON必须包含以下键：preferences, facts, episodes, tasks, relations。"
            "每个值为字符串，使用多段落自然语言描述。"
        )
        user_prompt = (
            "请基于以下对话记录总结用户记忆：\n\n"
            f"{full_text[:60000]}"
        )

        response = await llm_service.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=settings.OPENAI_MODEL,
            temperature=0.2,
            max_tokens=1200,
            use_cache=False
        )

        raw_content = response["choices"][0]["message"]["content"].strip()
        json_start = raw_content.find("{")
        json_end = raw_content.rfind("}")
        if json_start == -1 or json_end == -1:
            raise ValueError("LLM response is not valid JSON")

        parsed = json.loads(raw_content[json_start:json_end + 1])

        updated = {
            "preferences": str(parsed.get("preferences", "")).strip(),
            "facts": str(parsed.get("facts", "")).strip(),
            "episodes": str(parsed.get("episodes", "")).strip(),
            "tasks": str(parsed.get("tasks", "")).strip(),
            "relations": str(parsed.get("relations", "")).strip(),
        }

        for memory_type, content in updated.items():
            await memory_manager.update_user_memory(
                user_id=user_id,
                memory_type=memory_type,
                content=content
            )

        logger.info("memory_refresh_completed", user_id=user_id)
        return updated

    except Exception as e:
        logger.error("refresh_user_memory_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
