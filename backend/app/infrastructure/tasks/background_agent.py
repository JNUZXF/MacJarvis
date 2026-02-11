# File: backend/app/infrastructure/tasks/background_agent.py
# Purpose: Celery tasks for executing delegated agent tasks in background
from typing import Dict, Any
from datetime import datetime
import structlog
import asyncio

from app.infrastructure.tasks.celery_app import celery_app
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120, time_limit=1800)
def execute_delegated_task(
    self,
    task_id: str,
    user_id: str,
    task_description: str,
    context: Dict[str, Any]
) -> Dict:
    """
    Execute a delegated task using an independent agent instance.

    This task runs in a separate worker process and can execute
    long-running agent operations without blocking the main chat flow.

    Args:
        self: Task instance (bound)
        task_id: Delegated task ID
        user_id: User ID
        task_description: Task description
        context: Task context including chat history, files, etc.

    Returns:
        Execution result dictionary
    """
    try:
        logger.info(
            "delegated_task_started",
            task_id=task_id,
            user_id=user_id,
            celery_task_id=self.request.id,
            description=task_description[:100]
        )

        # Update task status to 'running'
        asyncio.run(_update_task_status(
            task_id=task_id,
            status='running',
            started_at=datetime.utcnow()
        ))

        # Build system prompt for background agent
        system_prompt = _build_background_agent_prompt(task_description, context)

        # Create user input from task description and context
        user_input = _build_user_input(task_description, context)

        # Execute agent task using MacAgent
        result = _execute_agent(user_input, system_prompt, user_id, task_id)

        # Update task status to 'completed' with result
        asyncio.run(_update_task_status(
            task_id=task_id,
            status='completed',
            result=result,
            completed_at=datetime.utcnow()
        ))

        logger.info(
            "delegated_task_completed",
            task_id=task_id,
            celery_task_id=self.request.id,
            result_length=len(result)
        )

        return {
            "status": "completed",
            "task_id": task_id,
            "result": result,
            "celery_task_id": self.request.id,
        }

    except Exception as exc:
        logger.error(
            "delegated_task_failed",
            task_id=task_id,
            celery_task_id=self.request.id,
            error=str(exc),
            error_type=type(exc).__name__
        )

        # Update task status to 'failed' with error
        try:
            asyncio.run(_update_task_status(
                task_id=task_id,
                status='failed',
                error=str(exc),
                completed_at=datetime.utcnow()
            ))
        except Exception as db_exc:
            logger.error(
                "failed_to_update_task_status",
                task_id=task_id,
                error=str(db_exc)
            )

        # Retry with exponential backoff if retries are available
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=120 * (2 ** self.request.retries))
        else:
            # Final failure
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(exc),
                "celery_task_id": self.request.id,
            }


def _build_background_agent_prompt(task_description: str, context: Dict[str, Any]) -> str:
    """
    Build system prompt for background agent.

    Args:
        task_description: Task description
        context: Task context

    Returns:
        System prompt string
    """
    base_prompt = """You are a background agent executing a delegated task.

**Your Role:**
- You are working independently to complete a specific task
- You have access to all the same tools as the main agent
- Focus on completing the task thoroughly and accurately
- Provide a comprehensive summary of your work and findings

**Task Context:**
The main agent has delegated the following task to you for independent execution.
Complete this task to the best of your ability and return detailed results.

**Important Guidelines:**
- Be thorough and systematic in your approach
- Use appropriate tools to gather information and complete the task
- If you encounter errors or limitations, document them clearly
- Provide clear, actionable results that the main agent can report to the user
- Your output will be sent back to the user via the main agent
"""

    # Add chat history if available
    chat_history = context.get("chat_history", [])
    if chat_history:
        base_prompt += "\n\n**Relevant Chat History:**\n"
        for msg in chat_history[-5:]:  # Include last 5 messages for context
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if content:
                base_prompt += f"{role}: {content[:200]}\n"

    # Add file context if available
    files = context.get("files", [])
    if files:
        base_prompt += "\n\n**Relevant Files:**\n"
        for file_path in files:
            base_prompt += f"- {file_path}\n"

    # Add additional context
    additional_info = context.get("additional_info", {})
    if additional_info:
        base_prompt += "\n\n**Additional Context:**\n"
        for key, value in additional_info.items():
            base_prompt += f"- {key}: {value}\n"

    return base_prompt


def _build_user_input(task_description: str, context: Dict[str, Any]) -> str:
    """
    Build user input for background agent.

    Args:
        task_description: Task description
        context: Task context

    Returns:
        User input string
    """
    user_input = f"""**Delegated Task:**

{task_description}

**Instructions:**
Please complete this task thoroughly and provide a detailed summary of:
1. What you did
2. What you found or accomplished
3. Any issues or limitations encountered
4. Final results or recommendations

Execute the task now and return your complete findings.
"""
    return user_input


def _execute_agent(
    user_input: str,
    system_prompt: str,
    user_id: str,
    task_id: str
) -> str:
    """
    Execute agent with given input.

    Args:
        user_input: User input
        system_prompt: System prompt
        user_id: User ID
        task_id: Task ID

    Returns:
        Agent output string
    """
    try:
        from agent.mac_agent import MacAgent
        from agent.core.config import load_openai_config

        # Load OpenAI config
        config = load_openai_config()

        # Create agent instance with custom system prompt
        agent = MacAgent(
            config=config,
            system_prompt=system_prompt
        )

        # Execute agent (non-streaming)
        result = agent.run(
            user_input=user_input,
            max_tool_turns=15  # Allow more tool turns for complex tasks
        )

        return result

    except Exception as e:
        logger.error(
            "agent_execution_failed",
            task_id=task_id,
            error=str(e)
        )
        raise


async def _update_task_status(
    task_id: str,
    status: str,
    result: str = None,
    error: str = None,
    started_at: datetime = None,
    completed_at: datetime = None
) -> None:
    """
    Update delegated task status in database.

    Args:
        task_id: Task ID
        status: New status
        result: Task result (optional)
        error: Error message (optional)
        started_at: Start timestamp (optional)
        completed_at: Completion timestamp (optional)
    """
    from app.infrastructure.database.connection import get_db_session
    from app.infrastructure.database.models import DelegatedTask
    from sqlalchemy import select

    async for db in get_db_session(settings):
        stmt = select(DelegatedTask).where(DelegatedTask.id == task_id)
        db_result = await db.execute(stmt)
        task = db_result.scalar_one_or_none()

        if task:
            task.status = status
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            if started_at is not None:
                task.started_at = started_at
            if completed_at is not None:
                task.completed_at = completed_at

            await db.commit()
            logger.info(
                "task_status_updated",
                task_id=task_id,
                status=status
            )
        else:
            logger.warning(
                "task_not_found_for_update",
                task_id=task_id
            )
        break  # Exit after first iteration
