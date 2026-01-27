# File: backend/agent/memory/manager.py
# Purpose: Orchestrate memory retrieval and context assembly for the agent.
from __future__ import annotations

from typing import Any

from agent.memory.store import EpisodicMemory, SemanticMemory, ShortTermMemory


class MemoryManager:
    def __init__(
        self,
        short_term: ShortTermMemory,
        episodic: EpisodicMemory,
        semantic: SemanticMemory,
        context_max_chars: int = 4000,
    ) -> None:
        self.short_term = short_term
        self.episodic = episodic
        self.semantic = semantic
        self.context_max_chars = context_max_chars

    def record_message(self, session_id: str, role: str, content: str) -> None:
        self.short_term.add_message(session_id, {"role": role, "content": content})

    def build_context(self, user_id: str, session_id: str, query: str) -> str:
        recent = self.short_term.get_context(session_id)
        episodes = self.episodic.recall(user_id, query, limit=3)
        knowledge = self.semantic.retrieve_knowledge(user_id, query, limit=5)

        parts: list[str] = []
        if knowledge:
            knowledge_text = "\n".join(f"- {item['content']}" for item in knowledge)
            parts.append(f"相关知识:\n{knowledge_text}")

        if episodes:
            episode_text = "\n".join(
                f"- {item.get('summary') or item.get('type')}" for item in episodes
            )
            parts.append(f"相关历史:\n{episode_text}")

        if recent:
            recent_text = "\n".join(f"{item['role']}: {item['content']}" for item in recent)
            parts.append(f"当前对话:\n{recent_text}")

        context = "\n\n".join(parts).strip()
        if len(context) > self.context_max_chars:
            context = context[: self.context_max_chars] + "..."
        return context

    def store_episode(
        self,
        user_id: str,
        session_id: str,
        episode_type: str,
        summary: str,
        content: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        return self.episodic.store_episode(user_id, session_id, episode_type, summary, content, metadata)
