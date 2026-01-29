# File: backend/app/services/conversation_history_service.py
# Purpose: Service for managing conversation history storage and export

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories import MessageRepository, SessionRepository
from app.services.markdown_exporter import MarkdownExporter

logger = logging.getLogger(__name__)


class ConversationHistoryService:
    """Service for managing conversation history storage and export"""

    def __init__(
        self,
        db_session: AsyncSession,
        markdown_exporter: Optional[MarkdownExporter] = None,
        base_path: str = "files"
    ):
        """
        Initialize the conversation history service

        Args:
            db_session: Database session
            markdown_exporter: Markdown exporter instance
            base_path: Base path for file storage
        """
        self.db_session = db_session
        self.message_repo = MessageRepository(db_session)
        self.session_repo = SessionRepository(db_session)
        self.markdown_exporter = markdown_exporter or MarkdownExporter(base_path)
        self.base_path = base_path

    async def save_message_with_metadata(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict]] = None,
        tool_call_results: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Save a message with detailed metadata

        Args:
            session_id: Session ID
            role: Message role (user, assistant, system, tool)
            content: Message content
            tool_calls: Tool calls information
            tool_call_results: Tool call results
            metadata: Additional metadata

        Returns:
            Message dictionary
        """
        import uuid

        message_id = str(uuid.uuid4())

        # Prepare metadata with timestamp
        msg_metadata = metadata or {}
        if "timestamp" not in msg_metadata:
            msg_metadata["timestamp"] = datetime.utcnow().isoformat()

        # Save to database
        message = await self.message_repo.create(
            message_id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_results=tool_call_results,
            metadata=msg_metadata
        )

        return {
            "id": message.id,
            "session_id": message.session_id,
            "role": message.role,
            "content": message.content,
            "tool_calls": message.tool_calls,
            "tool_call_results": message.tool_call_results,
            "metadata": message.metadata,
            "created_at": message.created_at.isoformat() if message.created_at else None
        }

    async def save_user_message(
        self,
        session_id: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Save a user message

        Args:
            session_id: Session ID
            content: Message content
            metadata: Additional metadata

        Returns:
            Message dictionary
        """
        return await self.save_message_with_metadata(
            session_id=session_id,
            role="user",
            content=content,
            metadata=metadata
        )

    async def save_assistant_message(
        self,
        session_id: str,
        content: str,
        tool_calls: Optional[List[Dict]] = None,
        tool_call_results: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Save an assistant message

        Args:
            session_id: Session ID
            content: Message content
            tool_calls: Tool calls information
            tool_call_results: Tool call results
            metadata: Additional metadata

        Returns:
            Message dictionary
        """
        return await self.save_message_with_metadata(
            session_id=session_id,
            role="assistant",
            content=content,
            tool_calls=tool_calls,
            tool_call_results=tool_call_results,
            metadata=metadata
        )

    async def save_tool_message(
        self,
        session_id: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Save a tool result message

        Args:
            session_id: Session ID
            content: Tool result content
            metadata: Additional metadata

        Returns:
            Message dictionary
        """
        return await self.save_message_with_metadata(
            session_id=session_id,
            role="tool",
            content=content,
            metadata=metadata
        )

    async def get_session_messages(
        self,
        session_id: str,
        include_system: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all messages for a session

        Args:
            session_id: Session ID
            include_system: Whether to include system messages

        Returns:
            List of message dictionaries
        """
        session = await self.session_repo.get_by_id(session_id, load_messages=True)

        if not session:
            logger.warning(f"Session {session_id} not found")
            return []

        messages = []
        for msg in session.messages:
            if not include_system and msg.role == "system":
                continue

            messages.append({
                "id": msg.id,
                "session_id": msg.session_id,
                "role": msg.role,
                "content": msg.content,
                "tool_calls": msg.tool_calls,
                "tool_call_results": msg.tool_call_results,
                "metadata": msg.metadata,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            })

        return messages

    async def export_session_to_markdown(
        self,
        session_id: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Export a session's conversation history to Markdown files

        Args:
            session_id: Session ID
            system_prompt: System prompt to export (optional)

        Returns:
            Dictionary with file paths for each export type
        """
        # Get all messages
        messages = await self.get_session_messages(session_id, include_system=False)

        # Extract system prompt from messages if not provided
        if system_prompt is None:
            session = await self.session_repo.get_by_id(session_id, load_messages=True)
            if session and session.messages:
                for msg in session.messages:
                    if msg.role == "system":
                        system_prompt = msg.content
                        break

        # Use default if still not found
        if system_prompt is None:
            system_prompt = "系统提示词未设置"

        # Export all files
        try:
            result = self.markdown_exporter.export_all(
                session_id=session_id,
                system_prompt=system_prompt,
                messages=messages
            )

            logger.info(f"Exported conversation history for session {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to export conversation history: {e}")
            raise

    async def auto_export_on_message(
        self,
        session_id: str,
        system_prompt: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Automatically export conversation history after a message is added

        Args:
            session_id: Session ID
            system_prompt: System prompt (optional)

        Returns:
            Export result or None if export is disabled
        """
        try:
            return await self.export_session_to_markdown(session_id, system_prompt)
        except Exception as e:
            logger.error(f"Auto-export failed for session {session_id}: {e}")
            return None

    async def get_conversation_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics about a conversation

        Args:
            session_id: Session ID

        Returns:
            Dictionary with conversation statistics
        """
        messages = await self.get_session_messages(session_id, include_system=True)

        stats = {
            "total_messages": len(messages),
            "user_messages": sum(1 for m in messages if m["role"] == "user"),
            "assistant_messages": sum(1 for m in messages if m["role"] == "assistant"),
            "tool_messages": sum(1 for m in messages if m["role"] == "tool"),
            "system_messages": sum(1 for m in messages if m["role"] == "system"),
            "total_tool_calls": 0,
            "first_message_at": None,
            "last_message_at": None
        }

        # Count tool calls
        for msg in messages:
            if msg.get("tool_calls"):
                stats["total_tool_calls"] += len(msg["tool_calls"])

        # Get timestamps
        if messages:
            stats["first_message_at"] = messages[0].get("created_at")
            stats["last_message_at"] = messages[-1].get("created_at")

        return stats
