# File: backend/app/services/markdown_exporter.py
# Purpose: Export conversation history to Markdown files

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class MarkdownExporter:
    """Service for exporting conversation history to Markdown files"""

    def __init__(self, base_path: str = "files"):
        """
        Initialize the Markdown exporter

        Args:
            base_path: Base directory for storing files
        """
        self.base_path = Path(base_path)

    def _ensure_directory(self, session_id: str) -> Path:
        """
        Ensure the conversation directory exists for a session

        Args:
            session_id: Session ID

        Returns:
            Path to the conversations directory
        """
        conv_dir = self.base_path / session_id / "conversations"
        conv_dir.mkdir(parents=True, exist_ok=True)
        return conv_dir

    def _format_timestamp(self, dt: datetime) -> str:
        """
        Format datetime to yyyymmdd-hhmmss string

        Args:
            dt: Datetime object

        Returns:
            Formatted timestamp string
        """
        return dt.strftime("%Y%m%d-%H%M%S")

    def export_system_prompt(
        self,
        session_id: str,
        system_prompt: str
    ) -> str:
        """
        Export system prompt to a Markdown file

        Args:
            session_id: Session ID
            system_prompt: System prompt content

        Returns:
            Path to the exported file
        """
        conv_dir = self._ensure_directory(session_id)
        file_path = conv_dir / "系统提示词.md"

        content = f"""# 系统提示词

{system_prompt}

---
*生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

        file_path.write_text(content, encoding="utf-8")
        return str(file_path)

    def export_simple_chat(
        self,
        session_id: str,
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        Export simple chat history (user and assistant only) to Markdown

        Args:
            session_id: Session ID
            messages: List of message dictionaries

        Returns:
            Path to the exported file
        """
        conv_dir = self._ensure_directory(session_id)
        file_path = conv_dir / "聊天记录.md"

        lines = ["# 聊天记录\n"]

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            created_at = msg.get("created_at")

            # Only include user and assistant messages
            if role not in ["user", "assistant"]:
                continue

            if created_at:
                if isinstance(created_at, str):
                    # Parse ISO format datetime
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except:
                        dt = datetime.now()
                else:
                    dt = created_at

                timestamp = self._format_timestamp(dt)
            else:
                timestamp = self._format_timestamp(datetime.now())

            lines.append(f"---{timestamp}：{role}---\n")
            lines.append(f"{content}\n\n")

        lines.append(f"---\n*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

        file_path.write_text("".join(lines), encoding="utf-8")
        return str(file_path)

    def export_full_chat(
        self,
        session_id: str,
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        Export full chat history (including tool calls) to Markdown

        Args:
            session_id: Session ID
            messages: List of message dictionaries

        Returns:
            Path to the exported file
        """
        conv_dir = self._ensure_directory(session_id)
        file_path = conv_dir / "完整聊天记录.md"

        lines = ["# 完整聊天记录（含工具调用）\n"]

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls")
            tool_call_results = msg.get("tool_call_results")
            created_at = msg.get("created_at")
            metadata = msg.get("metadata", {})

            if created_at:
                if isinstance(created_at, str):
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except:
                        dt = datetime.now()
                else:
                    dt = created_at

                timestamp = self._format_timestamp(dt)
            else:
                timestamp = self._format_timestamp(datetime.now())

            # Handle different message types
            if role == "user":
                lines.append(f"---{timestamp}：user---\n")
                lines.append(f"{content}\n\n")

            elif role == "assistant":
                lines.append(f"---{timestamp}：assistant---\n")
                lines.append(f"{content}\n\n")

                # If this assistant message has tool calls, add them
                if tool_calls:
                    tool_timestamp = metadata.get("tool_call_timestamp", timestamp)
                    lines.append(f"---{tool_timestamp}：tool---\n")
                    lines.append("**工具调用:**\n\n")

                    for i, tool_call in enumerate(tool_calls):
                        if isinstance(tool_call, dict):
                            tool_name = tool_call.get("function", {}).get("name", "unknown")
                            tool_args = tool_call.get("function", {}).get("arguments", "{}")

                            lines.append(f"**调用 #{i+1}: {tool_name}**\n\n")
                            lines.append("入参:\n```json\n")

                            # Pretty print JSON
                            try:
                                if isinstance(tool_args, str):
                                    args_obj = json.loads(tool_args)
                                else:
                                    args_obj = tool_args
                                lines.append(json.dumps(args_obj, indent=2, ensure_ascii=False))
                            except:
                                lines.append(str(tool_args))

                            lines.append("\n```\n\n")

                            # Add tool result if available
                            if tool_call_results and i < len(tool_call_results):
                                result = tool_call_results[i]
                                lines.append("出参:\n```json\n")
                                try:
                                    if isinstance(result, str):
                                        result_obj = json.loads(result)
                                    else:
                                        result_obj = result
                                    lines.append(json.dumps(result_obj, indent=2, ensure_ascii=False))
                                except:
                                    lines.append(str(result))
                                lines.append("\n```\n\n")

            elif role == "tool":
                # Tool result message (if stored separately)
                lines.append(f"---{timestamp}：tool---\n")
                lines.append("**工具返回结果:**\n\n")
                lines.append("```json\n")
                try:
                    if isinstance(content, str):
                        content_obj = json.loads(content)
                    else:
                        content_obj = content
                    lines.append(json.dumps(content_obj, indent=2, ensure_ascii=False))
                except:
                    lines.append(str(content))
                lines.append("\n```\n\n")

            elif role == "system":
                lines.append(f"---{timestamp}：system---\n")
                lines.append(f"{content}\n\n")

        lines.append(f"---\n*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

        file_path.write_text("".join(lines), encoding="utf-8")
        return str(file_path)

    def export_all(
        self,
        session_id: str,
        system_prompt: str,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Export all conversation files (system prompt, simple chat, full chat)

        Args:
            session_id: Session ID
            system_prompt: System prompt content
            messages: List of message dictionaries

        Returns:
            Dictionary with file paths for each export type
        """
        return {
            "system_prompt": self.export_system_prompt(session_id, system_prompt),
            "simple_chat": self.export_simple_chat(session_id, messages),
            "full_chat": self.export_full_chat(session_id, messages)
        }
