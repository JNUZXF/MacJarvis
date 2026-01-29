# File: backend/agent/prompts/__init__.py
# Purpose: Centralized prompt management for Mac Agent
# Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/agent/prompts/__init__.py

from agent.prompts.system_prompts import (
    BASE_SYSTEM_PROMPT,
    CLI_SYSTEM_PROMPT,
    build_system_prompt_with_paths,
    build_system_prompt_with_attachment,
    build_system_prompt_with_memory,
    build_extra_system_prompt,
)

__all__ = [
    "BASE_SYSTEM_PROMPT",
    "CLI_SYSTEM_PROMPT",
    "build_system_prompt_with_paths",
    "build_system_prompt_with_attachment",
    "build_system_prompt_with_memory",
    "build_extra_system_prompt",
]
