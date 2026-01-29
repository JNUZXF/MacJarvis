# File: backend/app/services/chat_service.py
# Purpose: Chat service orchestrating agent, memory, and tools
import base64
from pathlib import Path
from typing import Optional, AsyncIterator, List
import structlog

from app.services.llm_service import LLMService
from app.services.session_service import SessionService
from app.services.file_service import FileService
from app.services.conversation_history_service import ConversationHistoryService
from app.services.memory_integration_service import MemoryIntegrationService
from app.config import Settings
from app.core.agent.orchestrator import AgentOrchestrator
from app.core.tools.registry import ToolRegistry
from datetime import datetime
import json

logger = structlog.get_logger(__name__)


class ChatService:
    """
    High-level chat service that orchestrates:
    - LLM interactions
    - Session management
    - Memory integration
    - File attachments
    - Tool execution
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        session_service: SessionService,
        file_service: FileService,
        conversation_history_service: ConversationHistoryService,
        settings: Settings,
        memory_integration_service: Optional[MemoryIntegrationService] = None
    ):
        """
        Initialize chat service.

        Args:
            llm_service: LLM service for AI interactions
            session_service: Session management service
            file_service: File handling service
            conversation_history_service: Conversation history service
            settings: Application settings
            memory_integration_service: Optional memory integration service
        """
        self.llm = llm_service
        self.sessions = session_service
        self.files = file_service
        self.conversation_history = conversation_history_service
        self.settings = settings
        self.memory = memory_integration_service
    
    async def process_chat_message(
        self,
        user_id: str,
        session_id: str,
        message: str,
        model: Optional[str] = None,
        attachments: Optional[List[dict]] = None,
        stream: bool = True
    ) -> AsyncIterator[dict]:
        """
        Process a chat message with streaming response.
        
        Args:
            user_id: User ID
            session_id: Session ID
            message: User message
            model: Optional model override
            attachments: Optional file attachments
            stream: Whether to stream response
        
        Yields:
            Event dictionaries (content, tool_start, tool_result, error)
        """
        try:
            # Get or create session
            session = await self.sessions.get_session(
                user_id=user_id,
                session_id=session_id,
                load_messages=True
            )
            
            if not session:
                yield {
                    "type": "error",
                    "error": f"Session not found: {session_id}"
                }
                return
            
            # Update session title if it's a new session
            if session.get("title") == "新会话" and not session.get("messages"):
                title = self.sessions.create_session_title(message)
                await self.sessions.update_session_title(
                    user_id=user_id,
                    session_id=session_id,
                    title=title
                )
            
            # Add user message to session with timestamp
            user_msg_timestamp = datetime.utcnow()
            await self.sessions.add_message(
                session_id=session_id,
                role="user",
                content=message,
                metadata={"timestamp": user_msg_timestamp.isoformat()}
            )
            
            # Process attachments
            attachment_context = ""
            image_parts = []
            
            if attachments:
                attachment_context, image_parts = await self._process_attachments(
                    attachments
                )
            
            # Get memory context if memory service is available
            memory_context = ""
            if self.memory:
                memory_context = await self.memory.build_memory_context_prompt(user_id)

            # Build messages for LLM
            messages = self._build_llm_messages(
                message=message,
                attachment_context=attachment_context,
                image_parts=image_parts,
                history=session.get("messages", [])[-10:],  # Last 10 messages
                memory_context=memory_context
            )
            
            # Determine model
            model = model or self.settings.OPENAI_MODEL
            
            # Validate model
            if not self.settings.is_model_allowed(model):
                yield {
                    "type": "error",
                    "error": f"Model not allowed: {model}"
                }
                return
            
            logger.info(
                "chat_processing_started",
                user_id=user_id,
                session_id=session_id,
                model=model,
                message_length=len(message),
                has_attachments=bool(attachments)
            )
            
            # Stream LLM response
            assistant_content = ""
            
            if stream:
                response = await self.llm.chat_completion(
                    messages=messages,
                    model=model,
                    stream=True,
                    use_cache=False  # Don't cache streaming responses
                )
                
                async for chunk in response:
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    
                    if content:
                        assistant_content += content
                        yield {
                            "type": "content",
                            "content": content
                        }
            else:
                response = await self.llm.chat_completion(
                    messages=messages,
                    model=model,
                    stream=False,
                    use_cache=True
                )
                
                assistant_content = response["choices"][0]["message"]["content"]
                yield {
                    "type": "content",
                    "content": assistant_content
                }
            
            # Save assistant message with timestamp
            assistant_msg_timestamp = datetime.utcnow()
            await self.sessions.add_message(
                session_id=session_id,
                role="assistant",
                content=assistant_content,
                metadata={"timestamp": assistant_msg_timestamp.isoformat()}
            )

            # Extract and store memories in background (if memory service is available)
            if self.memory:
                try:
                    await self.memory.extract_and_store_memories(
                        user_id=user_id,
                        session_id=session_id,
                        user_message=message,
                        assistant_response=assistant_content,
                        background=True  # Run in background to not block response
                    )
                except Exception as memory_error:
                    logger.error(
                        "memory_extraction_failed",
                        user_id=user_id,
                        session_id=session_id,
                        error=str(memory_error)
                    )

            # Export conversation history to Markdown files
            try:
                system_prompt = self._build_system_prompt()
                await self.conversation_history.export_session_to_markdown(
                    session_id=session_id,
                    system_prompt=system_prompt
                )
                logger.info(
                    "conversation_exported",
                    session_id=session_id
                )
            except Exception as export_error:
                logger.error(
                    "conversation_export_failed",
                    session_id=session_id,
                    error=str(export_error)
                )

            logger.info(
                "chat_processing_completed",
                user_id=user_id,
                session_id=session_id,
                response_length=len(assistant_content)
            )
            
        except Exception as e:
            logger.error(
                "chat_processing_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            yield {
                "type": "error",
                "error": str(e)
            }
    
    async def _process_attachments(
        self,
        attachments: List[dict]
    ) -> tuple[str, List[dict]]:
        """
        Process file attachments.
        
        Args:
            attachments: List of attachment metadata
        
        Returns:
            Tuple of (text_context, image_parts)
        """
        context_parts = []
        image_parts = []
        
        for attachment in attachments:
            file_id = attachment.get("file_id")
            if not file_id:
                continue
            
            # Get file info (in production, this would query a database)
            # For now, we'll assume the file path is provided
            file_path = attachment.get("path")
            if not file_path:
                continue
            
            path = Path(file_path)
            if not path.exists():
                continue
            
            # Check if image
            content_type = attachment.get("content_type", "")
            if self.files.is_image_file(path, content_type):
                # Read and encode image
                raw = path.read_bytes()
                encoded = base64.b64encode(raw).decode("ascii")
                image_url = f"data:{content_type or 'image/png'};base64,{encoded}"
                image_parts.append({
                    "type": "image_url",
                    "image_url": {"url": image_url}
                })
            else:
                # Extract text
                text = self.files.extract_text(path)
                if text:
                    filename = attachment.get("filename", path.name)
                    context_parts.append(f"文件: {filename}\n{text}")
        
        context = "\n\n".join(context_parts).strip()
        return context, image_parts
    
    def _build_llm_messages(
        self,
        message: str,
        attachment_context: str,
        image_parts: List[dict],
        history: List[dict],
        memory_context: str = ""
    ) -> List[dict]:
        """
        Build messages array for LLM API.

        Args:
            message: Current user message
            attachment_context: Text from attachments
            image_parts: Image attachments
            history: Recent message history
            memory_context: User memory context

        Returns:
            List of message dictionaries
        """
        messages = [
            {
                "role": "system",
                "content": self._build_system_prompt(attachment_context, memory_context)
            }
        ]
        
        # Add recent history (excluding current message)
        for hist_msg in history[:-1]:  # Exclude the last message (current user message)
            if hist_msg.get("role") in ["user", "assistant"]:
                messages.append({
                    "role": hist_msg["role"],
                    "content": hist_msg.get("content", "")
                })
        
        # Add current user message
        if image_parts:
            # Multimodal message
            user_content = [
                {"type": "text", "text": message},
                *image_parts
            ]
        else:
            user_content = message
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        return messages
    
    def _build_system_prompt(
        self,
        attachment_context: str = "",
        memory_context: str = ""
    ) -> str:
        """
        Build system prompt with optional attachment and memory context.

        Args:
            attachment_context: Context from file attachments
            memory_context: User memory context

        Returns:
            System prompt string
        """
        base_prompt = """你是一个专业的 macOS 智能助手，可以帮助用户管理系统、排查问题、执行自动化任务。
你可以使用提供的工具来获取信息或执行操作。
在执行具有潜在风险的操作（如删除文件、修改系统设置）前，请务必仔细确认路径和参数。
请用中文回复用户。"""

        prompt_parts = [base_prompt]

        if memory_context:
            prompt_parts.append(f"\n\n{memory_context}")

        if attachment_context:
            prompt_parts.append(f"\n\n附件内容:\n{attachment_context}")

        return "".join(prompt_parts)
    
    async def generate_session_summary(
        self,
        session_id: str,
        max_length: int = 200
    ) -> str:
        """
        Generate a summary of a session.
        
        Args:
            session_id: Session ID
            max_length: Maximum summary length
        
        Returns:
            Summary text
        """
        try:
            # Get recent messages
            messages = await self.sessions.get_recent_messages(
                session_id=session_id,
                count=20
            )
            
            if not messages:
                return "空会话"
            
            # Build text for summarization
            text_parts = []
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if content:
                    text_parts.append(f"{role}: {content}")
            
            full_text = "\n".join(text_parts)
            
            # Use LLM to summarize
            summary = await self.llm.summarize_text(
                text=full_text,
                max_length=max_length
            )
            
            return summary
            
        except Exception as e:
            logger.error(
                "session_summary_failed",
                session_id=session_id,
                error=str(e)
            )
            return "摘要生成失败"

    async def process_chat_message_with_tools(
        self,
        user_id: str,
        session_id: str,
        message: str,
        tool_registry: ToolRegistry,
        model: Optional[str] = None,
        attachments: Optional[List[dict]] = None
    ) -> AsyncIterator[dict]:
        """
        Process a chat message with tool execution support.

        Args:
            user_id: User ID
            session_id: Session ID
            message: User message
            tool_registry: Tool registry for tool execution
            model: Optional model override
            attachments: Optional file attachments

        Yields:
            Event dictionaries (content, tool_start, tool_result, error)
        """
        try:
            # Get or create session
            session = await self.sessions.get_session(
                user_id=user_id,
                session_id=session_id,
                load_messages=True
            )

            if not session:
                yield {
                    "type": "error",
                    "error": f"Session not found: {session_id}"
                }
                return

            # Update session title if needed
            if session.get("title") == "新会话" and not session.get("messages"):
                title = self.sessions.create_session_title(message)
                await self.sessions.update_session_title(
                    user_id=user_id,
                    session_id=session_id,
                    title=title
                )

            # Add user message with timestamp
            user_msg_timestamp = datetime.utcnow()
            await self.sessions.add_message(
                session_id=session_id,
                role="user",
                content=message,
                metadata={"timestamp": user_msg_timestamp.isoformat()}
            )

            # Process attachments
            attachment_context = ""
            image_parts = []

            if attachments:
                attachment_context, image_parts = await self._process_attachments(
                    attachments
                )

            # Build user input
            if image_parts:
                user_input = [
                    {"type": "text", "text": message},
                    *image_parts
                ]
            else:
                user_input = message

            # Get recent history for context
            history = session.get("messages", [])[-10:]
            extra_messages = []
            for hist_msg in history[:-1]:  # Exclude current message
                if hist_msg.get("role") in ["user", "assistant"]:
                    extra_messages.append({
                        "role": hist_msg["role"],
                        "content": hist_msg.get("content", "")
                    })

            # Get memory context if memory service is available
            memory_context = ""
            if self.memory:
                memory_context = await self.memory.build_memory_context_prompt(user_id)

            # Create agent orchestrator
            llm_client = self.llm.client
            system_prompt = self._build_system_prompt(attachment_context, memory_context)
            orchestrator = AgentOrchestrator(
                client=llm_client,
                registry=tool_registry,
                settings=self.settings,
                system_prompt=system_prompt
            )

            # Run agent with tools
            assistant_content = ""
            tool_calls = []
            tool_call_results = []
            tool_call_timestamp = None

            async for event in orchestrator.run_stream(
                user_input=user_input,
                extra_messages=extra_messages
            ):
                event_type = event.get("type")

                if event_type == "content":
                    content = event.get("content", "")
                    assistant_content += content
                    yield {
                        "type": "content",
                        "content": content
                    }

                elif event_type == "tool_start":
                    # Record tool call timestamp
                    if tool_call_timestamp is None:
                        tool_call_timestamp = datetime.utcnow()

                    tool_call = {
                        "id": event.get("tool_call_id"),
                        "type": "function",
                        "function": {
                            "name": event.get("name"),
                            "arguments": json.dumps(event.get("args", {}), ensure_ascii=False)
                        }
                    }
                    tool_calls.append(tool_call)

                    yield {
                        "type": "tool_start",
                        "tool_call_id": event.get("tool_call_id"),
                        "name": event.get("name"),
                        "args": event.get("args")
                    }

                elif event_type == "tool_result":
                    result = event.get("result", {})
                    tool_call_results.append(result)

                    yield {
                        "type": "tool_result",
                        "tool_call_id": event.get("tool_call_id"),
                        "result": result
                    }

            # Save assistant message with tool calls and results
            assistant_msg_timestamp = datetime.utcnow()
            metadata = {"timestamp": assistant_msg_timestamp.isoformat()}

            if tool_call_timestamp:
                metadata["tool_call_timestamp"] = tool_call_timestamp.isoformat()

            await self.sessions.add_message(
                session_id=session_id,
                role="assistant",
                content=assistant_content,
                tool_calls=tool_calls if tool_calls else None,
                tool_call_results=tool_call_results if tool_call_results else None,
                metadata=metadata
            )

            # Extract and store memories in background (if memory service is available)
            if self.memory:
                try:
                    await self.memory.extract_and_store_memories(
                        user_id=user_id,
                        session_id=session_id,
                        user_message=message,
                        assistant_response=assistant_content,
                        background=True  # Run in background to not block response
                    )
                except Exception as memory_error:
                    logger.error(
                        "memory_extraction_failed",
                        user_id=user_id,
                        session_id=session_id,
                        error=str(memory_error)
                    )

            # Export conversation history to Markdown files
            try:
                system_prompt = self._build_system_prompt()
                await self.conversation_history.export_session_to_markdown(
                    session_id=session_id,
                    system_prompt=system_prompt
                )
                logger.info(
                    "conversation_exported",
                    session_id=session_id
                )
            except Exception as export_error:
                logger.error(
                    "conversation_export_failed",
                    session_id=session_id,
                    error=str(export_error)
                )

            logger.info(
                "chat_with_tools_completed",
                user_id=user_id,
                session_id=session_id,
                response_length=len(assistant_content),
                tool_calls_count=len(tool_calls)
            )

        except Exception as e:
            logger.error(
                "chat_with_tools_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            yield {
                "type": "error",
                "error": str(e)
            }
