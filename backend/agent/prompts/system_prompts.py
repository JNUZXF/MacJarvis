# File: backend/agent/prompts/system_prompts.py
# Purpose: System prompts for Mac Agent
# Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/agent/prompts/system_prompts.py

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
    
    ## 工具使用原则
    1. **优先使用已注册工具**：你必须优先使用提供的工具来完成任务
    2. **安全第一**：在执行具有潜在风险的操作（如删除文件、修改系统设置）前，请务必仔细确认路径和参数
    3. **明确限制**：如果我请求存在安全风险或超出工具能力，直接说明限制并给出可行替代方案
    4. **禁止危险操作**：绝不执行会清空系统目录、破坏安全设置或泄露敏感信息的操作
    
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


# ============================================================================
# CLI System Prompt - 命令行工具提示词
# ============================================================================

CLI_SYSTEM_PROMPT = dedent("""
    你是 macOS 管理智能体。
    你必须优先使用已注册工具完成任务。
    如果我请求存在安全风险或超出工具能力，直接说明限制并给出可行替代方案。
    绝不执行会清空系统目录、破坏安全设置或泄露敏感信息的操作。
""").strip()


# ============================================================================
# Dynamic Prompt Builders - 动态提示词构建器
# ============================================================================

def build_system_prompt_with_paths(allowed_paths: list[str]) -> str:
    """
    Build system prompt with user's allowed paths.
    
    Args:
        allowed_paths: List of allowed file system paths
    
    Returns:
        System prompt with path restrictions
    """
    if not allowed_paths:
        return BASE_SYSTEM_PROMPT
    
    paths_text = dedent("""
        ## 路径访问限制
        我只能访问以下路径：
    """).strip()
    
    for path in allowed_paths:
        paths_text += f"\n- {path}"
    
    return f"{BASE_SYSTEM_PROMPT}\n\n{paths_text}".strip()


def build_system_prompt_with_attachment(attachment_context: str) -> str:
    """
    Build system prompt with attachment context.
    
    Args:
        attachment_context: Context from file attachments
    
    Returns:
        System prompt with attachment context
    """
    if not attachment_context:
        return BASE_SYSTEM_PROMPT
    
    attachment_section = dedent(f"""
        ## 附件内容
        {attachment_context}
    """).strip()
    
    return f"{BASE_SYSTEM_PROMPT}\n\n{attachment_section}".strip()


def build_system_prompt_with_memory(memory_context: str) -> str:
    """
    Build system prompt with memory context.
    
    Args:
        memory_context: Context from conversation memory
    
    Returns:
        System prompt with memory context
    """
    if not memory_context:
        return BASE_SYSTEM_PROMPT
    
    memory_section = dedent(f"""
        ## 对话历史摘要
        {memory_context}
    """).strip()
    
    return f"{BASE_SYSTEM_PROMPT}\n\n{memory_section}".strip()


# ============================================================================
# Extra System Prompts - 额外系统提示词
# ============================================================================

def build_extra_system_prompt(
    attachment_context: str = "",
    memory_context: str = "",
    custom_instructions: str = ""
) -> str:
    """
    Build extra system prompt with multiple contexts.
    
    Args:
        attachment_context: Context from file attachments
        memory_context: Context from conversation memory
        custom_instructions: Custom user instructions
    
    Returns:
        Combined extra system prompt
    """
    parts = []
    
    if attachment_context:
        parts.append(dedent(f"""
            ## 附件内容
            {attachment_context}
        """).strip())
    
    if memory_context:
        parts.append(dedent(f"""
            ## 对话历史摘要
            {memory_context}
        """).strip())
    
    if custom_instructions:
        parts.append(dedent(f"""
            ## 我自定义指令
            {custom_instructions}
        """).strip())
    
    return "\n\n".join(parts).strip()
