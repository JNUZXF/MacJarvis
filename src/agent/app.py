import sys

from agent.core.agent import Agent
from agent.core.client import OpenAIClient
from agent.core.config import load_openai_config
from agent.tools.mac_tools import build_default_tools
from agent.tools.registry import ToolRegistry


SYSTEM_PROMPT = """你是 macOS 管理智能体。
你必须优先使用已注册工具完成任务。
如果用户请求存在安全风险或超出工具能力，直接说明限制并给出可行替代方案。
绝不执行会清空系统目录、破坏安全设置或泄露敏感信息的操作。
"""


def main() -> int:
    if len(sys.argv) < 2:
        user_input = sys.stdin.read().strip()
    else:
        user_input = " ".join(sys.argv[1:]).strip()
    if not user_input:
        return 1
    config = load_openai_config()
    client = OpenAIClient(config)
    registry = ToolRegistry(build_default_tools())
    agent = Agent(client, registry, SYSTEM_PROMPT)
    output = agent.run(user_input, config.max_tool_turns)
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
