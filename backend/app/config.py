# File: backend/app/config.py
# Purpose: Unified configuration management with pydantic-settings for multi-environment support
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Literal
import json


class Settings(BaseSettings):
    """
    Application settings with type-safe configuration management.
    Supports multiple environments (development, staging, production).
    """
    model_config = SettingsConfigDict(
        env_file=[".env", "../.env"],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Application Configuration
    APP_NAME: str = "MacOS Agent Platform"
    ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    # CORS配置：当allow_credentials=True时，不能使用["*"]，必须明确指定允许的源
    # 支持通过环境变量配置，格式：
    # JSON格式：CORS_ORIGINS=["http://localhost:18889","http://localhost:3000"]
    # 或逗号分隔：CORS_ORIGINS=http://localhost:18889,http://localhost:3000
    CORS_ORIGINS: str = "http://localhost:18889,http://localhost:3000,http://127.0.0.1:18889,http://127.0.0.1:3000"
    
    # LLM Configuration
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com"
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT_S: int = 60
    OPENAI_MAX_TOOL_TURNS: int = 8
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = ""
    LLM_REQUEST_TIMEOUT: int = 30
    LLM_CACHE_ENABLED: bool = True
    LLM_CACHE_TTL: int = 3600
    
    # Allowed Models
    ALLOWED_MODELS: list[str] = [
        "openai/gpt-4o-mini",
        "gpt-4o-mini",
        "anthropic/claude-haiku-4.5",
        "google/gemini-2.5-flash",
    ]
    
    # Database Configuration
    # PostgreSQL 配置（推荐用于生产环境）
    # 格式: postgresql+asyncpg://user:password@host:port/database
    # 示例: postgresql+asyncpg://postgres:password@localhost:5433/mac_agent
    # 注意: 默认使用端口 5433 以避免与 Cursor 编辑器或其他服务冲突
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/mac_agent"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False
    # SQLite 配置（仅用于开发环境，生产环境不推荐）
    # SQLite 并发写入时容易出现 "database is locked"
    SQLITE_BUSY_TIMEOUT_MS: int = 30000
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50
    
    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # File Upload Configuration
    UPLOAD_DIR: str = "./backend_data/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ATTACHMENT_TEXT_LIMIT: int = 10000
    
    # Memory System Configuration
    MEMORY_WINDOW_SIZE: int = 10
    MEMORY_TTL_S: int = 3600
    MEMORY_CONTEXT_MAX_CHARS: int = 4000
    MEMORY_SUMMARY_TRIGGER: int = 24
    MEMORY_KEEP_LAST: int = 8
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Monitoring Configuration
    ENABLE_TRACING: bool = False
    JAEGER_ENDPOINT: str = "http://localhost:14268/api/traces"
    
    # Security Configuration
    ALLOWED_ROOTS: list[str] = []
    AGENT_ALLOWED_ROOTS: str = ""  # Colon-separated paths for backward compatibility
    
    @property
    def effective_llm_config(self) -> dict:
        """Determine which LLM configuration to use (OpenAI or OpenRouter)"""
        use_openrouter = False
        if self.OPENROUTER_API_KEY and self.OPENROUTER_BASE_URL:
            if not self.OPENAI_API_KEY or not self.OPENAI_BASE_URL or self.OPENAI_BASE_URL == "https://api.openai.com":
                use_openrouter = True
        
        if use_openrouter:
            return {
                "api_key": self.OPENROUTER_API_KEY,
                "base_url": self.OPENROUTER_BASE_URL,
                "model": self.OPENAI_MODEL,
                "timeout_s": self.OPENAI_TIMEOUT_S,
                "max_tool_turns": self.OPENAI_MAX_TOOL_TURNS,
            }
        else:
            return {
                "api_key": self.OPENAI_API_KEY,
                "base_url": self.OPENAI_BASE_URL or "https://api.openai.com",
                "model": self.OPENAI_MODEL,
                "timeout_s": self.OPENAI_TIMEOUT_S,
                "max_tool_turns": self.OPENAI_MAX_TOOL_TURNS,
            }
    
    def is_model_allowed(self, model: str) -> bool:
        """Check if a model is in the allowed list"""
        return model in self.ALLOWED_MODELS
    
    def get_cors_origins(self) -> list[str]:
        """Parse CORS_ORIGINS env into list"""
        raw = (self.CORS_ORIGINS or "").strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    def get_allowed_roots(self) -> list[str]:
        """Get list of allowed root paths from both sources"""
        roots = list(self.ALLOWED_ROOTS)
        if self.AGENT_ALLOWED_ROOTS:
            roots.extend(self.AGENT_ALLOWED_ROOTS.split(":"))
        return [r.strip() for r in roots if r.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure singleton pattern.
    """
    return Settings()
