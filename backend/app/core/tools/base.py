# File: backend/agent/tools/base.py
# Purpose: Define the protocol for tool implementations.
from typing import Any, Protocol


class Tool(Protocol):
    name: str
    description: str
    parameters: dict[str, Any]

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        ...
