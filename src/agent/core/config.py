from dataclasses import dataclass, replace
import os


ALLOWED_MODELS = [
    "openai/gpt-4o-mini",
    "gpt-4o-mini",  # 兼容旧版本
    "anthropic/claude-haiku-4.5",
    "google/gemini-2.5-flash",
]


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    base_url: str
    model: str
    timeout_s: int
    max_tool_turns: int


def is_model_allowed(model: str) -> bool:
    return model in ALLOWED_MODELS


def with_model(config: OpenAIConfig, model: str) -> OpenAIConfig:
    return replace(config, model=model)


def load_openai_config() -> OpenAIConfig:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    timeout_s = int(os.getenv("OPENAI_TIMEOUT_S", "60"))
    max_tool_turns = int(os.getenv("OPENAI_MAX_TOOL_TURNS", "8"))
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")
    return OpenAIConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_s=timeout_s,
        max_tool_turns=max_tool_turns,
    )
