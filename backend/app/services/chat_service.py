# File: backend/app/services/chat_service.py
# Purpose: Chat service orchestrating agent, memory, and tools
import base64
from pathlib import Path
from typing import Optional, AsyncIterator, List
import structlog
import asyncio

from app.services.llm_service import LLMService
from app.services.session_service import SessionService
from app.services.file_service import FileService
from app.services.conversation_history_service import ConversationHistoryService
from app.services.tts_service import TextSegmenter
from app.api.v1.tts import synthesize_speech_stream
from app.config import Settings
from app.core.agent.orchestrator import AgentOrchestrator
from app.core.tools.registry import ToolRegistry
from app.infrastructure.database.connection import get_session_maker
from agent.tools.mac_tools import build_default_tools
from datetime import datetime
import json

logger = structlog.get_logger(__name__)

from textwrap import dedent


# ============================================================================
# Base System Prompt - 基础系统提示词
# ============================================================================

BASE_SYSTEM_PROMPT = dedent("""
    你是一个专业的 macOS 智能助手，可以帮助我管理系统、排查问题、执行自动化任务。
    
    ## 核心能力
    - 系统监控：查看系统状态、进程信息、资源使用情况
    - 文件管理：搜索、读取、创建、管理文件和目录
    - 文本处理：使用grep搜索、正则匹配、日志分析
    - 网络诊断：检查网络配置、端口状态、DNS设置
    - 应用管理：启动应用、管理已安装程序
    - 开发工具：Git操作、端口管理、文件对比
    - 记忆管理：记住用户的偏好、事实、重要对话、任务和关系
    
    ## 工具使用原则
    1. **优先使用已注册工具**：你必须优先使用提供的工具来完成任务
    2. **安全第一**：在执行具有潜在风险的操作（如删除文件、修改系统设置）前，请务必仔细确认路径和参数
    3. **明确限制**：如果我请求存在安全风险或超出工具能力，直接说明限制并给出可行替代方案
    4. **禁止危险操作**：绝不执行会清空系统目录、破坏安全设置或泄露敏感信息的操作

    ## 记忆系统使用指南
    你拥有update_memory工具来记住关于用户的重要信息。当用户表达以下内容时，应该使用此工具：
    
    1. **偏好记忆 (preferences)**：用户的明确偏好
       - 例如："我喜欢简洁的回复"、"我是素食主义者"、"我习惯用VSCode"
       - 何时更新：用户明确表达喜好、习惯、风格偏好时
    
    2. **事实记忆 (facts)**：关于用户的客观信息
       - 例如：姓名、职业、工作地点、家庭成员、使用的技术栈
       - 何时更新：用户分享个人信息、工作背景、技术能力时
    
    3. **情景记忆 (episodes)**：重要的对话片段或事件
       - 例如："上周讨论了巴黎旅行计划"、"昨天解决了数据库连接问题"
       - 何时更新：完成重要任务、讨论重要话题、解决关键问题后
    
    4. **任务记忆 (tasks)**：进行中的工作状态
       - 例如："正在开发用户认证模块"、"需要优化API性能"
       - 何时更新：用户提到新任务、更新任务进度、完成任务时
    
    5. **关系记忆 (relations)**：实体间的关联
       - 例如："Alice是我的项目经理"、"项目X使用Python和FastAPI"
       - 何时更新：用户提到人际关系、项目技术栈、组织结构时
    
    **记忆更新原则**：
    - 主动识别：在对话中主动识别值得记住的信息
    - 及时更新：当获得新信息时立即更新相应的记忆类型
    - 简洁描述：用自然语言简洁描述，避免冗长
    - 累积更新：新信息应该追加到现有记忆中，而不是替换
    - 强制触发：当用户明确说“请记住/记住这点/请记录”或直接陈述个人事实与偏好时，必须调用 update_memory 工具

    ## 文件保存规范
    - 你可以在任何位置创建文件，但所有需要长期保存的产出内容默认写入固定目录：~/.mac_agent/records/
    - 按内容类型存放到对应子目录，例如报告保存到 ~/.mac_agent/records/report/，总结保存到 ~/.mac_agent/records/summary/
    - 若因用户要求必须存到其他位置，先说明原因，再执行
    
    ## 响应规范
    - 使用中文回复我
    - 提供清晰、准确的信息
    - 在执行操作前说明将要做什么
    - 操作完成后总结结果

    # 工作原则
    - 文件操作：你不清楚当前我的文件夹的具体名称和路径，在操作时需要先了解对应文件夹下的相应文件有哪些，再进行操作

    # 你的回答风格
    - 你需要用日常对话的形式来回答我的问题，不使用分点等书面语言，语气自然活泼
""").strip()




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
        settings: Settings
    ):
        """
        Initialize chat service.

        Args:
            llm_service: LLM service for AI interactions
            session_service: Session management service
            file_service: File handling service
            conversation_history_service: Conversation history service
            settings: Application settings
        """
        self.llm = llm_service
        self.sessions = session_service
        self.files = file_service
        self.conversation_history = conversation_history_service
        self.settings = settings
        self.tool_registry = self._build_tool_registry()

    def _build_tool_registry(self) -> ToolRegistry:
        """Build tool registry with database session factory and celery app injected."""
        tools = build_default_tools()
        session_maker = get_session_maker(self.settings)

        # Import celery app
        from app.infrastructure.tasks.celery_app import celery_app

        # Inject dependencies into tools
        for tool in tools:
            tool_name = getattr(tool, "name", "")

            # Inject db_session_factory for memory and delegation tools
            if tool_name in ("update_memory", "delegate_task", "check_delegated_tasks"):
                tool.db_session_factory = session_maker

            # Inject celery_app for delegation tool
            if tool_name == "delegate_task":
                tool.celery_app = celery_app

        return ToolRegistry(tools)
    
    async def process_chat_message(
        self,
        user_id: str,
        session_id: str,
        message: str,
        model: Optional[str] = None,
        attachments: Optional[List[dict]] = None,
        stream: bool = True,
        tts_enabled: bool = False,
        tts_voice: str = "longyingtao_v3",
        tts_model: str = "cosyvoice-v3-flash"
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
            # Use tool-enabled pipeline for all requests
            async for event in self.process_chat_message_with_tools(
                user_id=user_id,
                session_id=session_id,
                message=message,
                tool_registry=self.tool_registry,
                model=model,
                attachments=attachments,
                tts_enabled=tts_enabled,
                tts_voice=tts_voice,
                tts_model=tts_model
            ):
                yield event
            return
            logger.info(
                "chat_process_enter",
                user_id=user_id,
                session_id=session_id,
                message_length=len(message),
                stream=stream,
                tts_enabled=tts_enabled,
            )

            # Get or create session
            logger.info(
                "chat_load_session_start",
                user_id=user_id,
                session_id=session_id,
            )
            session = await self.sessions.get_session(
                user_id=user_id,
                session_id=session_id,
                load_messages=True
            )
            logger.info(
                "chat_load_session_done",
                user_id=user_id,
                session_id=session_id,
                found=bool(session),
                loaded_message_count=len(session.get("messages", [])) if session else 0,
            )
            
            if not session:
                yield {
                    "type": "error",
                    "error": f"Session not found: {session_id}"
                }
                return
            
            # Update session title if it's a new session
            if session.get("title") == "新会话" and not session.get("messages"):
                logger.info(
                    "chat_update_session_title_start",
                    user_id=user_id,
                    session_id=session_id,
                )
                title = self.sessions.create_session_title(message)
                await self.sessions.update_session_title(
                    user_id=user_id,
                    session_id=session_id,
                    title=title
                )
                logger.info(
                    "chat_update_session_title_done",
                    user_id=user_id,
                    session_id=session_id,
                )
            
            # Add user message to session with timestamp
            user_msg_timestamp = datetime.utcnow()
            logger.info(
                "chat_add_user_message_start",
                user_id=user_id,
                session_id=session_id,
            )
            await self.sessions.add_message(
                session_id=session_id,
                role="user",
                content=message,
                metadata={"timestamp": user_msg_timestamp.isoformat()}
            )
            logger.info(
                "chat_add_user_message_done",
                user_id=user_id,
                session_id=session_id,
            )
            
            # Process attachments
            attachment_context = ""
            image_parts = []
            
            if attachments:
                attachment_context, image_parts = await self._process_attachments(
                    attachments
                )
            
            # Memory context is now handled by Agent's update_memory tool
            memory_context = ""

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
            
            # 初始化TTS分段器（如果启用）
            segmenter = None
            segment_id = 0
            tts_tasks = []
            
            if tts_enabled:
                segmenter = TextSegmenter(
                    min_length=10,
                    max_length=200,
                    prefer_length=50
                )
            
            if stream:
                # Get async generator directly from streaming method
                response = self.llm._chat_completion_stream(
                    messages=messages,
                    model=model
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
                        
                        # TTS分段处理
                        if segmenter:
                            segments = segmenter.add_text(content)
                            for segment_text in segments:
                                current_segment_id = segment_id
                                segment_id += 1
                                
                                # 记录需要合成的段落信息
                                tts_tasks.append({
                                    "segment_text": segment_text,
                                    "segment_id": current_segment_id,
                                    "tts_voice": tts_voice,
                                    "tts_model": tts_model
                                })
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
            
            # 处理剩余的文本片段（刷新缓冲区）
            if segmenter:
                final_segment = segmenter.flush()
                if final_segment:
                    current_segment_id = segment_id
                    segment_id += 1
                    
                    tts_tasks.append({
                        "segment_text": final_segment,
                        "segment_id": current_segment_id,
                        "tts_voice": tts_voice,
                        "tts_model": tts_model
                    })
            
            # 按顺序合成并返回TTS音频事件
            for task_info in tts_tasks:
                async for tts_event in self._synthesize_and_stream_segment(
                    segment_text=task_info["segment_text"],
                    segment_id=task_info["segment_id"],
                    tts_voice=task_info["tts_voice"],
                    tts_model=task_info["tts_model"]
                ):
                    yield tts_event
            
            # Save assistant message with timestamp
            assistant_msg_timestamp = datetime.utcnow()
            await self.sessions.add_message(
                session_id=session_id,
                role="assistant",
                content=assistant_content,
                metadata={"timestamp": assistant_msg_timestamp.isoformat()}
            )

            # Memory extraction is now handled by Agent's update_memory tool
            # Agent will automatically call update_memory when it identifies important information

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
        base_prompt = BASE_SYSTEM_PROMPT

        prompt_parts = [base_prompt]

        if memory_context:
            prompt_parts.append(f"\n\n{memory_context}")

        if attachment_context:
            prompt_parts.append(f"\n\n附件内容:\n{attachment_context}")

        return "".join(prompt_parts)
    
    async def _synthesize_and_stream_segment(
        self,
        segment_text: str,
        segment_id: int,
        tts_voice: str,
        tts_model: str
    ) -> AsyncIterator[dict]:
        """
        合成单个文本段落并流式返回音频数据
        
        Args:
            segment_text: 要合成的文本段落
            segment_id: 段落ID
            tts_voice: TTS音色
            tts_model: TTS模型
            
        Yields:
            TTS事件字典
        """
        try:
            # 发送段落开始事件
            yield {
                "type": "tts_segment_start",
                "segment_id": segment_id,
                "text": segment_text
            }
            
            # 流式合成音频
            audio_chunks = []
            async for audio_chunk in synthesize_speech_stream(
                text=segment_text,
                model=tts_model,
                voice=tts_voice
            ):
                # 将音频数据编码为base64
                audio_base64 = base64.b64encode(audio_chunk).decode('utf-8')
                audio_chunks.append(audio_chunk)
                
                # 返回音频数据块
                yield {
                    "type": "tts_audio",
                    "segment_id": segment_id,
                    "audio_chunk": audio_base64,
                    "is_final": False
                }
            
            # 发送段落结束事件
            yield {
                "type": "tts_audio",
                "segment_id": segment_id,
                "audio_chunk": "",
                "is_final": True
            }
            
            yield {
                "type": "tts_segment_end",
                "segment_id": segment_id
            }
            
            logger.info(
                "tts_segment_synthesized",
                segment_id=segment_id,
                text_length=len(segment_text),
                audio_chunks=len(audio_chunks)
            )
            
        except Exception as e:
            logger.error(
                "tts_synthesis_failed",
                segment_id=segment_id,
                text=segment_text,
                error=str(e)
            )
            # TTS失败不影响文本显示，只记录错误
            yield {
                "type": "tts_error",
                "segment_id": segment_id,
                "error": str(e)
            }
    
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
        attachments: Optional[List[dict]] = None,
        tts_enabled: bool = False,
        tts_voice: str = "longyingtao_v3",
        tts_model: str = "cosyvoice-v3-flash"
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

            # Force memory tool call for explicit "remember" intent
            memory_trigger_phrases = ["请记住", "记住这", "记住：", "记住:", "我的爱好", "我喜欢"]
            should_force_memory_tool = any(phrase in message for phrase in memory_trigger_phrases)

            # Get recent history for context
            history = session.get("messages", [])[-10:]
            extra_messages = []
            for hist_msg in history[:-1]:  # Exclude current message
                if hist_msg.get("role") in ["user", "assistant"]:
                    extra_messages.append({
                        "role": hist_msg["role"],
                        "content": hist_msg.get("content", "")
                    })

            # Memory context is now handled by Agent's update_memory tool
            memory_context = ""

            # Determine model
            model = model or self.settings.OPENAI_MODEL

            # Validate model
            if not self.settings.is_model_allowed(model):
                yield {
                    "type": "error",
                    "error": f"Model not allowed: {model}"
                }
                return

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
            
            # 初始化TTS分段器（如果启用）
            segmenter = None
            segment_id = 0
            tts_tasks = []
            
            if tts_enabled:
                segmenter = TextSegmenter(
                    min_length=10,
                    max_length=200,
                    prefer_length=50
                )

            async for event in orchestrator.run_stream(
                user_input=user_input,
                extra_messages=extra_messages,
                model=model,
                tool_context={"user_id": user_id, "session_id": session_id},
                tool_choice=(
                    {"type": "function", "function": {"name": "update_memory"}}
                    if should_force_memory_tool
                    else None
                ),
            ):
                event_type = event.get("type")

                if event_type == "content":
                    content = event.get("content", "")
                    assistant_content += content
                    yield {
                        "type": "content",
                        "content": content
                    }
                    
                    # TTS分段处理
                    if segmenter:
                        segments = segmenter.add_text(content)
                        for segment_text in segments:
                            current_segment_id = segment_id
                            segment_id += 1
                            
                            # 记录需要合成的段落信息
                            tts_tasks.append({
                                "segment_text": segment_text,
                                "segment_id": current_segment_id,
                                "tts_voice": tts_voice,
                                "tts_model": tts_model
                            })

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
            
            # 处理剩余的文本片段（刷新缓冲区）
            if segmenter:
                final_segment = segmenter.flush()
                if final_segment:
                    current_segment_id = segment_id
                    segment_id += 1
                    
                    tts_tasks.append({
                        "segment_text": final_segment,
                        "segment_id": current_segment_id,
                        "tts_voice": tts_voice,
                        "tts_model": tts_model
                    })
            
            # 按顺序合成并返回TTS音频事件
            for task_info in tts_tasks:
                async for tts_event in self._synthesize_and_stream_segment(
                    segment_text=task_info["segment_text"],
                    segment_id=task_info["segment_id"],
                    tts_voice=task_info["tts_voice"],
                    tts_model=task_info["tts_model"]
                ):
                    yield tts_event

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

            # Memory extraction is now handled by Agent's update_memory tool
            # Agent will automatically call update_memory when it identifies important information

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
