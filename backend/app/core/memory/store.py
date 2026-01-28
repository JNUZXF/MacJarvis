# File: backend/agent/memory/store.py
# Purpose: Provide short-term, episodic, and semantic memory stores for the agent.
from __future__ import annotations

import json
import time
import uuid
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from agent.core.config import OpenAIConfig


def _now_ts() -> int:
    return int(time.time())


def _score_text(query: str, text: str) -> int:
    if not query or not text:
        return 0
    terms = [t for t in query.lower().split() if t]
    hay = text.lower()
    return sum(hay.count(term) for term in terms)


class ShortTermMemory:
    def __init__(self, window_size: int = 10, ttl_s: int = 3600) -> None:
        self.window_size = window_size
        self.ttl_s = ttl_s
        self._store: dict[str, list[dict[str, Any]]] = {}
        self._updated_at: dict[str, float] = {}

    def _prune(self) -> None:
        now = time.time()
        expired = [sid for sid, ts in self._updated_at.items() if now - ts > self.ttl_s]
        for sid in expired:
            self._store.pop(sid, None)
            self._updated_at.pop(sid, None)

    def add_message(self, session_id: str, message: dict[str, Any]) -> None:
        self._prune()
        messages = self._store.setdefault(session_id, [])
        messages.append(message)
        if len(messages) > self.window_size:
            self._store[session_id] = messages[-self.window_size:]
        self._updated_at[session_id] = time.time()

    def get_context(self, session_id: str) -> list[dict[str, Any]]:
        self._prune()
        return list(self._store.get(session_id, []))

    def clear(self, session_id: str) -> None:
        self._store.pop(session_id, None)
        self._updated_at.pop(session_id, None)


class EpisodicMemory:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._ensure_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    summary TEXT,
                    content TEXT,
                    metadata TEXT,
                    created_at INTEGER NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_episodes_user ON episodes(user_id)")
            conn.commit()

    def store_episode(
        self,
        user_id: str,
        session_id: str,
        episode_type: str,
        summary: str,
        content: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        episode_id = str(uuid.uuid4())
        payload = json.dumps(content, ensure_ascii=False)
        meta = json.dumps(metadata or {}, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO episodes (id, user_id, session_id, type, summary, content, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (episode_id, user_id, session_id, episode_type, summary, payload, meta, _now_ts()),
            )
            conn.commit()
        return episode_id

    def recall(self, user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, type, summary, content, metadata, created_at
                FROM episodes
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, max(limit * 5, limit)),
            ).fetchall()

        scored = []
        for row in rows:
            summary = row["summary"] or ""
            content = row["content"] or ""
            score = _score_text(query, summary + " " + content)
            scored.append((score, row))

        scored.sort(key=lambda item: (item[0], item[1]["created_at"]), reverse=True)
        results = []
        for score, row in scored[:limit]:
            results.append(
                {
                    "id": row["id"],
                    "type": row["type"],
                    "summary": row["summary"],
                    "content": json.loads(row["content"] or "{}"),
                    "metadata": json.loads(row["metadata"] or "{}"),
                    "created_at": row["created_at"],
                    "score": score,
                }
            )
        return results


@dataclass
class SemanticMemory:
    db_path: Path
    embedding_config: OpenAIConfig | None = None
    embedding_model: str = "text-embedding-3-small"

    def __post_init__(self) -> None:
        self._ensure_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    embedding TEXT,
                    created_at INTEGER NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_semantic_user ON semantic_memory(user_id)")
            conn.commit()

    def _embedding_available(self) -> bool:
        return self.embedding_config is not None and bool(self.embedding_config.api_key)

    def _get_embedding(self, text: str) -> list[float] | None:
        if not self._embedding_available():
            return None
        config = self.embedding_config
        assert config is not None
        base_url = config.base_url.rstrip("/")
        url = f"{base_url}/v1/embeddings" if not base_url.endswith("/v1") else f"{base_url}/embeddings"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        }
        payload = {"model": self.embedding_model, "input": text}
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=config.timeout_s)
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except (httpx.HTTPError, KeyError, IndexError):
            return None

    def store_knowledge(
        self,
        user_id: str,
        knowledge: str,
        category: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        knowledge_id = str(uuid.uuid4())
        embedding = self._get_embedding(knowledge)
        meta = json.dumps(metadata or {}, ensure_ascii=False)
        embedding_json = json.dumps(embedding) if embedding else None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO semantic_memory (id, user_id, category, content, metadata, embedding, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (knowledge_id, user_id, category, knowledge, meta, embedding_json, _now_ts()),
            )
            conn.commit()
        return knowledge_id

    def retrieve_knowledge(self, user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, category, content, metadata, embedding, created_at
                FROM semantic_memory
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()

        query_embedding = self._get_embedding(query)
        scored: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            content = row["content"] or ""
            if query_embedding and row["embedding"]:
                stored = json.loads(row["embedding"])
                score = _cosine_similarity(query_embedding, stored)
            else:
                score = float(_score_text(query, content))
            scored.append((score, row))

        scored.sort(key=lambda item: (item[0], item[1]["created_at"]), reverse=True)
        results = []
        for score, row in scored[:limit]:
            results.append(
                {
                    "id": row["id"],
                    "category": row["category"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"] or "{}"),
                    "created_at": row["created_at"],
                    "score": score,
                }
            )
        return results


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
