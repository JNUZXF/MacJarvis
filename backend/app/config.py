# File: backend/app/config.py
# Purpose: Unified configuration management with pydantic-settings for multi-environment support
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    """
    Application settings with type-safe configuration management.
    Supports multiple environments (development, staging, production).
    """
    model_config = SettingsConfigDict(
        env_file=".env",
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
    CORS_ORIGINS: list[str] = ["*"]
    
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
    DATABASE_URL: str = "sqlite+aiosqlite:///./backend_data/app.db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False
    
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
