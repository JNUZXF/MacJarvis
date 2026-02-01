# File: backend/agent/tools/media/__init__.py
# Purpose: 媒体处理工具模块
from agent.tools.media.processor import (
    CaptureScreenshotTool,
    CompressImagesTool,
    GetVideoInfoTool,
)

__all__ = [
    "CompressImagesTool",
    "CaptureScreenshotTool",
    "GetVideoInfoTool",
]
