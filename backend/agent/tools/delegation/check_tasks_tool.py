# File: backend/agent/tools/delegation/check_tasks_tool.py
# Purpose: Tool for checking status of delegated background tasks
from dataclasses import dataclass
from typing import Any, Dict, List
import asyncio
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CheckDelegatedTasksTool:
    """检查后台智能体任务状态的工具"""

    name: str = "check_delegated_tasks"
    description: str = """检查后台智能体的任务状态和结果。适用于:
    - 查看所有待处理和进行中的任务
    - 获取已完成任务的结果
    - 检查失败任务的错误信息

    该工具会返回当前用户的所有委托任务,包括:
    - 任务ID和描述
    - 任务状态(pending/running/completed/failed)
    - 执行时间
    - 结果或错误信息(如果有)

    当有新完成的任务时,你应该主动通知用户并报告结果。"""

    parameters: Dict[str, Any] = None
    db_session_factory = None  # Will be injected

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "status_filter": {
                        "type": "string",
                        "enum": ["all", "pending", "running", "completed", "failed"],
                        "description": "过滤特定状态的任务,默认为'all'显示所有任务"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回的最大任务数量,默认为10",
                        "default": 10
                    }
                },
                "required": []
            }

    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task status check

        Args:
            args: Dictionary with optional status_filter and limit

        Returns:
            Result dictionary with task list
        """
        status_filter = args.get("status_filter", "all")
        limit = args.get("limit", 10)

        # Get user_id from context
        user_id = args.get("user_id")
        if not user_id:
            return {
                "ok": False,
                "error": "user_id is required in context"
            }

        try:
            # Try to run in event loop if available
            loop = asyncio.get_running_loop()
            future = asyncio.ensure_future(
                self._async_check(user_id, status_filter, limit)
            )
            # Wait for result synchronously
            result = asyncio.get_event_loop().run_until_complete(future) if not future.done() else future.result()
            return result
        except RuntimeError:
            # Fallback for non-async contexts
            try:
                result = asyncio.run(self._async_check(user_id, status_filter, limit))
                return result
            except Exception as e:
                logger.error("check_tasks_failed", error=str(e))
                return {
                    "ok": False,
                    "error": f"Failed to check tasks: {str(e)}"
                }
        except Exception as e:
            logger.error("check_tasks_failed", error=str(e))
            return {
                "ok": False,
                "error": f"Failed to check tasks: {str(e)}"
            }

    async def _async_check(
        self,
        user_id: str,
        status_filter: str,
        limit: int
    ) -> Dict[str, Any]:
        """
        Async task checking implementation

        Args:
            user_id: User identifier
            status_filter: Status filter
            limit: Maximum number of tasks to return

        Returns:
            Result dictionary with task list
        """
        if not self.db_session_factory:
            return {
                "ok": False,
                "error": "Database session factory not configured"
            }

        try:
            from app.infrastructure.database.models import DelegatedTask
            from sqlalchemy import select, desc

            async with self.db_session_factory() as db:
                # Build query
                stmt = select(DelegatedTask).where(DelegatedTask.user_id == user_id)

                # Apply status filter
                if status_filter != "all":
                    stmt = stmt.where(DelegatedTask.status == status_filter)

                # Order by created_at descending and limit
                stmt = stmt.order_by(desc(DelegatedTask.created_at)).limit(limit)

                # Execute query
                result = await db.execute(stmt)
                tasks = result.scalars().all()

                # Convert tasks to dict format
                tasks_data = []
                new_completed_count = 0

                for task in tasks:
                    task_info = {
                        "task_id": task.id,
                        "description": task.task_description,
                        "status": task.status,
                        "created_at": task.created_at.isoformat() if task.created_at else None,
                        "started_at": task.started_at.isoformat() if task.started_at else None,
                        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    }

                    # Include result or error based on status
                    if task.status == "completed":
                        task_info["result"] = task.result
                        if not task.notified:
                            new_completed_count += 1
                    elif task.status == "failed":
                        task_info["error"] = task.error

                    tasks_data.append(task_info)

                # Mark new completed tasks as notified
                if new_completed_count > 0:
                    from sqlalchemy import update
                    stmt = (
                        update(DelegatedTask)
                        .where(DelegatedTask.user_id == user_id)
                        .where(DelegatedTask.status == "completed")
                        .where(DelegatedTask.notified == 0)
                        .values(notified=1)
                    )
                    await db.execute(stmt)
                    await db.commit()

                logger.info(
                    "tasks_checked",
                    user_id=user_id,
                    total_tasks=len(tasks),
                    new_completed=new_completed_count
                )

                return {
                    "ok": True,
                    "data": {
                        "tasks": tasks_data,
                        "total_count": len(tasks),
                        "new_completed_count": new_completed_count,
                        "message": (
                            f"发现 {new_completed_count} 个新完成的任务!"
                            if new_completed_count > 0
                            else "没有新完成的任务"
                        )
                    }
                }

        except Exception as e:
            logger.error("async_check_failed", error=str(e))
            return {
                "ok": False,
                "error": str(e)
            }
