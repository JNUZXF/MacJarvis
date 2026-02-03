# File: backend/agent/tools/memory/update_tool.py
# Purpose: Tool for updating user memory
from dataclasses import dataclass
from typing import Any, Dict
import asyncio
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class UpdateMemoryTool:
    """更新用户记忆工具"""

    name: str = "update_memory"
    description: str = """更新用户的记忆信息。当用户表达以下内容时使用此工具:
    - preferences: 用户偏好(如"我喜欢简洁的回复"、"我是素食主义者")
    - facts: 客观事实(如姓名、职业、家庭成员、地址等)
    - episodes: 重要对话片段(如"上周讨论了巴黎旅行计划")
    - tasks: 进行中的任务(如项目进度、待办事项)
    - relations: 实体间关系(如"Alice是Bob的经理"、"项目X属于团队Y")
    
    记忆内容应该用自然语言描述,简洁明了。"""
    
    parameters: Dict[str, Any] = None
    db_session_factory = None  # Will be injected

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "memory_type": {
                        "type": "string",
                        "enum": ["preferences", "facts", "episodes", "tasks", "relations"],
                        "description": "记忆类型: preferences(偏好), facts(事实), episodes(情景), tasks(任务), relations(关系)"
                    },
                    "content": {
                        "type": "string",
                        "description": "记忆内容,用自然语言描述,可以是多个段落"
                    }
                },
                "required": ["memory_type", "content"]
            }

    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute memory update

        Args:
            args: Dictionary with memory_type and content

        Returns:
            Result dictionary with ok status
        """
        memory_type = args.get("memory_type", "")
        content = args.get("content", "")

        if not memory_type or not content:
            return {
                "ok": False,
                "error": "memory_type and content are required"
            }

        # Get user_id from context (will be set by the orchestrator)
        user_id = args.get("user_id")
        if not user_id:
            return {
                "ok": False,
                "error": "user_id is required in context"
            }

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_update(user_id, memory_type, content))
            return {
                "ok": True,
                "data": {
                    "status": "scheduled",
                    "memory_type": memory_type
                }
            }
        except RuntimeError:
            # Fallback for non-async contexts (may block)
            try:
                result = asyncio.run(self._async_update(user_id, memory_type, content))
                return result
            except Exception as e:
                logger.error("update_memory_tool_failed", error=str(e))
                return {
                    "ok": False,
                    "error": f"Failed to update memory: {str(e)}"
                }
        except Exception as e:
            logger.error("update_memory_tool_failed", error=str(e))
            return {
                "ok": False,
                "error": f"Failed to update memory: {str(e)}"
            }

    async def _async_update(
        self,
        user_id: str,
        memory_type: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Async memory update implementation

        Args:
            user_id: User identifier
            memory_type: Type of memory
            content: Memory content

        Returns:
            Result dictionary
        """
        if not self.db_session_factory:
            return {
                "ok": False,
                "error": "Database session factory not configured"
            }

        try:
            from app.services.memory_manager import MemoryManager

            async with self.db_session_factory() as db:
                memory_manager = MemoryManager(db)
                existing = await memory_manager.get_user_memory(user_id)
                current = (existing.get(memory_type) or "").strip()
                incoming = content.strip()

                if current:
                    if incoming in current:
                        merged = current
                    else:
                        merged = f"{current}\n\n{incoming}"
                else:
                    merged = incoming

                success = await memory_manager.update_user_memory(
                    user_id=user_id,
                    memory_type=memory_type,
                    content=merged
                )

                if success:
                    return {
                        "ok": True,
                        "data": {
                            "message": f"成功更新{memory_type}记忆",
                            "memory_type": memory_type,
                            "content_length": len(merged)
                        }
                    }
                else:
                    return {
                        "ok": False,
                        "error": "Failed to update memory in database"
                    }

        except Exception as e:
            logger.error("async_update_failed", error=str(e))
            return {
                "ok": False,
                "error": str(e)
            }
