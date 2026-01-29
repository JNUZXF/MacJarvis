# File: backend/app/services/memory_integration_service.py
# Purpose: Integrate memory system into chat workflow
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

from backend.app.services.memory_extractor import MemoryExtractor
from backend.app.services.memory_manager import MemoryManager
from backend.app.infrastructure.database.models import Message

logger = logging.getLogger(__name__)


class MemoryIntegrationService:
    """
    Service to integrate memory system into the chat workflow

    Responsibilities:
    1. Extract memories from conversations
    2. Inject user context into system prompts
    3. Background memory extraction
    """

    def __init__(
        self,
        memory_extractor: MemoryExtractor,
        memory_manager: MemoryManager
    ):
        """
        Initialize memory integration service

        Args:
            memory_extractor: Memory extraction service
            memory_manager: Memory management service
        """
        self.extractor = memory_extractor
        self.manager = memory_manager

    # ============ Memory Extraction ============

    async def extract_and_store_memories(
        self,
        user_id: str,
        session_id: str,
        user_message: str,
        assistant_response: str,
        background: bool = False
    ) -> Dict[str, int]:
        """
        Extract memories from a conversation turn and store them

        Args:
            user_id: User identifier
            session_id: Session identifier
            user_message: User's message
            assistant_response: Assistant's response
            background: Whether to run in background (non-blocking)

        Returns:
            Dictionary with counts of extracted memories
        """
        if background:
            # Run extraction in background without blocking
            asyncio.create_task(
                self._extract_and_store_internal(
                    user_id, session_id, user_message, assistant_response
                )
            )
            return {"status": "background"}
        else:
            # Run extraction synchronously
            return await self._extract_and_store_internal(
                user_id, session_id, user_message, assistant_response
            )

    async def _extract_and_store_internal(
        self,
        user_id: str,
        session_id: str,
        user_message: str,
        assistant_response: str
    ) -> Dict[str, int]:
        """Internal method to extract and store memories"""
        try:
            # Extract memories from the conversation
            extracted = await self.extractor.extract_from_single_message(
                user_message=user_message,
                assistant_response=assistant_response,
                user_id=user_id,
                session_id=session_id
            )

            # Store extracted memories
            counts = await self.manager.add_extracted_memories(
                extracted=extracted,
                user_id=user_id,
                session_id=session_id
            )

            logger.info(
                f"Extracted and stored memories for user {user_id}, "
                f"session {session_id}: {counts}"
            )

            return counts

        except Exception as e:
            logger.error(
                f"Error extracting/storing memories for user {user_id}: {e}",
                exc_info=True
            )
            return {
                "preferences": 0,
                "facts": 0,
                "tasks": 0,
                "relations": 0,
                "error": str(e)
            }

    async def extract_from_recent_messages(
        self,
        user_id: str,
        session_id: str,
        messages: List[Message],
        max_messages: int = 10
    ) -> Dict[str, int]:
        """
        Extract memories from recent conversation history

        Args:
            user_id: User identifier
            session_id: Session identifier
            messages: List of message objects
            max_messages: Maximum messages to analyze

        Returns:
            Dictionary with counts of extracted memories
        """
        try:
            # Format messages for extraction
            formatted_messages = []
            for msg in messages[-max_messages:]:
                if msg.role in ["user", "assistant"] and msg.content:
                    formatted_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })

            if len(formatted_messages) < 2:
                logger.info("Not enough messages for extraction")
                return {"preferences": 0, "facts": 0, "tasks": 0, "relations": 0}

            # Extract memories
            extracted = await self.extractor.extract_from_messages(
                messages=formatted_messages,
                user_id=user_id,
                session_id=session_id
            )

            # Store extracted memories
            counts = await self.manager.add_extracted_memories(
                extracted=extracted,
                user_id=user_id,
                session_id=session_id
            )

            logger.info(
                f"Extracted memories from recent history for user {user_id}: {counts}"
            )

            return counts

        except Exception as e:
            logger.error(
                f"Error extracting from recent messages: {e}",
                exc_info=True
            )
            return {"preferences": 0, "facts": 0, "tasks": 0, "relations": 0}

    # ============ Context Injection ============

    async def build_memory_context_prompt(
        self,
        user_id: str,
        max_items: int = 10
    ) -> str:
        """
        Build a context prompt with user's memories

        Args:
            user_id: User identifier
            max_items: Maximum items per memory type

        Returns:
            Formatted context string for system prompt
        """
        try:
            # Get user context
            context = await self.manager.get_user_context(
                user_id=user_id,
                max_items_per_type=max_items
            )

            # Build context sections
            sections = []

            # Preferences section
            if context["preferences"]:
                pref_lines = ["## User Preferences"]
                for pref in context["preferences"]:
                    pref_lines.append(
                        f"- **{pref['key']}** ({pref['category']}): {pref['value']}"
                    )
                sections.append("\n".join(pref_lines))

            # Facts section
            if context["facts"]:
                fact_lines = ["## User Information"]
                for fact in context["facts"]:
                    fact_lines.append(
                        f"- **{fact['subject']}** ({fact['type']}): {fact['value']}"
                    )
                sections.append("\n".join(fact_lines))

            # Active tasks section
            if context["active_tasks"]:
                task_lines = ["## Active Tasks"]
                for task in context["active_tasks"]:
                    progress_str = f" ({task['progress']}%)" if task['progress'] > 0 else ""
                    task_lines.append(
                        f"- [{task['priority'].upper()}] {task['title']}{progress_str}"
                    )
                sections.append("\n".join(task_lines))

            # Relations section
            if context["relations"]:
                rel_lines = ["## Known Relationships"]
                for rel in context["relations"]:
                    rel_lines.append(
                        f"- {rel['subject']} {rel['relation']} {rel['object']}"
                    )
                sections.append("\n".join(rel_lines))

            # Combine all sections
            if sections:
                prompt = "# User Context\n\n"
                prompt += "\n\n".join(sections)
                prompt += "\n\nUse this context to personalize your responses and be aware of the user's preferences, background, and ongoing tasks."
                return prompt
            else:
                return ""

        except Exception as e:
            logger.error(f"Error building memory context: {e}", exc_info=True)
            return ""

    async def get_relevant_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> Dict[str, List[Dict]]:
        """
        Get memories relevant to a specific query

        Args:
            user_id: User identifier
            query: Query string
            limit: Maximum items per type

        Returns:
            Dictionary with relevant memories
        """
        # For now, just return recent memories
        # In future, could implement semantic search
        try:
            preferences = await self.manager.get_preferences(user_id, limit=limit)
            facts = await self.manager.get_facts(user_id, limit=limit)
            tasks = await self.manager.get_tasks(user_id, status="active", limit=limit)
            relations = await self.manager.get_relations(user_id, limit=limit)

            return {
                "preferences": [
                    {
                        "key": p.preference_key,
                        "value": p.preference_value,
                        "category": p.category
                    }
                    for p in preferences
                ],
                "facts": [
                    {
                        "subject": f.subject,
                        "value": f.fact_value,
                        "type": f.fact_type
                    }
                    for f in facts
                ],
                "tasks": [
                    {
                        "title": t.title,
                        "status": t.status,
                        "priority": t.priority
                    }
                    for t in tasks
                ],
                "relations": [
                    {
                        "subject": r.subject_entity,
                        "relation": r.relation_type,
                        "object": r.object_entity
                    }
                    for r in relations
                ]
            }

        except Exception as e:
            logger.error(f"Error getting relevant memories: {e}", exc_info=True)
            return {"preferences": [], "facts": [], "tasks": [], "relations": []}

    # ============ Memory Statistics ============

    async def get_user_memory_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get a summary of user's memory state

        Args:
            user_id: User identifier

        Returns:
            Dictionary with memory statistics
        """
        try:
            from backend.app.services.memory_consolidator import MemoryConsolidator

            # Get statistics
            consolidator = MemoryConsolidator(self.manager.db)
            stats = await consolidator.get_memory_statistics(user_id)

            # Add last interaction time
            # (Would need to query from sessions/messages)

            return stats

        except Exception as e:
            logger.error(f"Error getting memory summary: {e}", exc_info=True)
            return {"error": str(e)}


def format_memories_for_display(memories: Dict[str, List[Dict]]) -> str:
    """
    Format memories for display to user

    Args:
        memories: Dictionary with memory lists

    Returns:
        Formatted string
    """
    lines = []

    if memories.get("preferences"):
        lines.append("**Your Preferences:**")
        for pref in memories["preferences"]:
            lines.append(f"  - {pref['key']}: {pref['value']}")

    if memories.get("facts"):
        lines.append("\n**About You:**")
        for fact in memories["facts"]:
            lines.append(f"  - {fact['subject']}: {fact['value']}")

    if memories.get("tasks"):
        lines.append("\n**Your Active Tasks:**")
        for task in memories["tasks"]:
            lines.append(f"  - [{task['priority']}] {task['title']}")

    if memories.get("relations"):
        lines.append("\n**Known Relationships:**")
        for rel in memories["relations"]:
            lines.append(f"  - {rel['subject']} {rel['relation']} {rel['object']}")

    return "\n".join(lines) if lines else "No memories stored yet."
