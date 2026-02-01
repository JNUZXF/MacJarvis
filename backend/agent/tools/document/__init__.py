# File: backend/agent/tools/document/__init__.py
# Purpose: 文档处理工具模块
from agent.tools.document.processor import (
    BatchSummarizeDocumentsTool,
    ExtractTextFromDocumentsTool,
)

__all__ = [
    "BatchSummarizeDocumentsTool",
    "ExtractTextFromDocumentsTool",
]
