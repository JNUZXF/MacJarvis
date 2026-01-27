# File: backend/tests/conftest.py
# Purpose: Provide shared pytest fixtures for backend API testing.
import importlib
import sys

import pytest


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("MEMORY_SUMMARY_TRIGGER", "9999")
    monkeypatch.setenv("MEMORY_KEEP_LAST", "5")
    monkeypatch.setenv("MEMORY_WINDOW_SIZE", "5")
    monkeypatch.setenv("MEMORY_TTL_S", "3600")
    monkeypatch.setenv("MEMORY_CONTEXT_MAX_CHARS", "2000")
    monkeypatch.setenv("ATTACHMENT_TEXT_LIMIT", "2000")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-small")

    module_name = "backend.server.app"
    if module_name in sys.modules:
        del sys.modules[module_name]
    app_module = importlib.import_module(module_name)

    def fake_chat_completions(self, messages, tools=None, stream=False):
        if stream:
            def gen():
                yield {"choices": [{"delta": {"content": "测试响应"}}]}
            return gen()
        return {"choices": [{"message": {"content": "摘要"}}]}

    monkeypatch.setattr(app_module.OpenAIClient, "chat_completions", fake_chat_completions, raising=True)

    data_dir = tmp_path / "backend_data"
    app_module.DATA_DIR = data_dir
    app_module.USER_PATHS_FILE = data_dir / "user_paths.json"
    app_module.UPLOAD_DIR = data_dir / "uploads"
    app_module.UPLOAD_INDEX_FILE = data_dir / "uploads.json"
    app_module.MEMORY_DB_PATH = data_dir / "memory.sqlite"

    app_module.memory_manager = app_module.MemoryManager(
        short_term=app_module.ShortTermMemory(
            window_size=app_module.MEMORY_WINDOW_SIZE,
            ttl_s=app_module.MEMORY_TTL_S,
        ),
        episodic=app_module.EpisodicMemory(app_module.MEMORY_DB_PATH),
        semantic=app_module.SemanticMemory(
            app_module.MEMORY_DB_PATH,
            embedding_config=None,
            embedding_model=app_module.EMBEDDING_MODEL,
        ),
        context_max_chars=app_module.MEMORY_CONTEXT_MAX_CHARS,
    )
    app_module.USER_STORE.clear()

    from fastapi.testclient import TestClient

    return TestClient(app_module.app)
