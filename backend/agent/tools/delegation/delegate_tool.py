# File: backend/agent/tools/delegation/delegate_tool.py
# Purpose: Tool for delegating tasks to background agents
from dataclasses import dataclass
from typing import Any, Dict
import asyncio
import uuid
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DelegateTaskTool:
    """将任务委托给后台智能体的工具"""

    name: str = "delegate_task"
    description: str = """将复杂或耗时的任务委托给后台智能体执行。适用于以下场景:
    - 需要长时间运行的任务(如分析大量文件、生成复杂报告)
    - 可以独立完成的任务(不需要频繁与用户交互)
    - 需要并行执行的任务(不想阻塞当前对话)

    后台智能体会在独立的环境中执行任务，完成后会自动通知你。你可以使用check_delegated_tasks工具查询任务状态和结果。

    注意: 委托的任务应该有明确的目标和完成标准。"""

    parameters: Dict[str, Any] = None
    db_session_factory = None  # Will be injected
    celery_app = None  # Will be injected

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "任务的详细描述,包括目标、要求和期望的输出格式"
                    },
                    "context": {
                        "type": "object",
                        "description": "任务所需的上下文信息,如相关文件路径、参数配置等",
                        "properties": {
                            "chat_history": {
                                "type": "array",
                                "description": "相关的聊天历史记录",
                                "items": {"type": "object"}
                            },
                            "files": {
                                "type": "array",
                                "description": "相关的文件路径列表",
                                "items": {"type": "string"}
                            },
                            "additional_info": {
                                "type": "object",
                                "description": "其他需要传递的信息"
                            }
                        }
                    }
                },
                "required": ["task_description"]
            }

    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task delegation

        Args:
            args: Dictionary with task_description and optional context

        Returns:
            Result dictionary with task_id
        """
        task_description = args.get("task_description", "")
        context = args.get("context", {})

        if not task_description:
            return {
                "ok": False,
                "error": "task_description is required"
            }

        # Get user_id and session_id from context
        user_id = args.get("user_id")
        session_id = args.get("session_id")

        if not user_id or not session_id:
            return {
                "ok": False,
                "error": "user_id and session_id are required in context"
            }

        try:
            # Try to run in event loop if available
            loop = asyncio.get_running_loop()
            task_id = str(uuid.uuid4())
            loop.create_task(
                self._async_delegate(task_id, user_id, session_id, task_description, context)
            )
            return {
                "ok": True,
                "data": {
                    "task_id": task_id,
                    "status": "pending",
                    "message": f"任务已委托给后台智能体执行 (ID: {task_id[:8]}...)",
                    "note": "使用check_delegated_tasks工具查询任务进度和结果"
                }
            }
        except RuntimeError:
            # Fallback for non-async contexts
            try:
                task_id = str(uuid.uuid4())
                asyncio.run(
                    self._async_delegate(task_id, user_id, session_id, task_description, context)
                )
                return {
                    "ok": True,
                    "data": {
                        "task_id": task_id,
                        "status": "pending",
                        "message": f"任务已委托给后台智能体执行 (ID: {task_id[:8]}...)"
                    }
                }
            except Exception as e:
                logger.error("delegate_task_failed", error=str(e))
                return {
                    "ok": False,
                    "error": f"Failed to delegate task: {str(e)}"
                }
        except Exception as e:
            logger.error("delegate_task_failed", error=str(e))
            return {
                "ok": False,
                "error": f"Failed to delegate task: {str(e)}"
            }

    async def _async_delegate(
        self,
        task_id: str,
        user_id: str,
        session_id: str,
        task_description: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Async task delegation implementation

        Args:
            task_id: Unique task identifier
            user_id: User identifier
            session_id: Session identifier
            task_description: Task description
            context: Task context

        Returns:
            Result dictionary
        """
        if not self.db_session_factory:
            logger.error("db_session_factory_not_configured")
            raise ValueError("Database session factory not configured")

        try:
            from app.infrastructure.database.models import DelegatedTask

            async with self.db_session_factory() as db:
                # Create delegated task record
                delegated_task = DelegatedTask(
                    id=task_id,
                    user_id=user_id,
                    session_id=session_id,
                    task_description=task_description,
                    context=context,
                    status='pending',
                    created_at=datetime.utcnow()
                )

                db.add(delegated_task)
                await db.commit()

                logger.info(
                    "delegated_task_created",
                    task_id=task_id,
                    user_id=user_id,
                    description=task_description[:100]
                )

            # Launch Celery background task
            if self.celery_app:
                from app.infrastructure.tasks.background_agent import execute_delegated_task
                celery_result = execute_delegated_task.delay(
                    task_id=task_id,
                    user_id=user_id,
                    task_description=task_description,
                    context=context
                )

                # Update with celery task ID
                async with self.db_session_factory() as db:
                    from sqlalchemy import select
                    stmt = select(DelegatedTask).where(DelegatedTask.id == task_id)
                    result = await db.execute(stmt)
                    task = result.scalar_one_or_none()
                    if task:
                        task.celery_task_id = celery_result.id
                        await db.commit()

                logger.info(
                    "celery_task_launched",
                    task_id=task_id,
                    celery_task_id=celery_result.id
                )

            return {
                "ok": True,
                "data": {
                    "task_id": task_id,
                    "status": "delegated"
                }
            }

        except Exception as e:
            logger.error("async_delegate_failed", error=str(e), task_id=task_id)
            raise
