"""
File: backend/tests/test_agent_shell_integration.py
Purpose: Integration test for Agent using ExecuteShellCommandTool
Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/test_agent_shell_integration.py
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent.tools.mac_tools import build_default_tools
from agent.tools.registry import ToolRegistry


def test_tool_registry():
    """测试工具注册表包含新工具"""
    print("\n=== 测试: 验证工具注册表 ===")
    
    # 构建工具列表
    tools = build_default_tools()
    registry = ToolRegistry(tools)
    
    # 获取OpenAI格式的工具列表
    openai_tools = registry.openai_tools()
    tool_names = [tool["function"]["name"] for tool in openai_tools]
    
    print(f"总工具数: {len(tool_names)}")
    print(f"是否包含 execute_shell_command: {'execute_shell_command' in tool_names}")
    
    # 打印前10个工具
    print("\n前10个工具:")
    for i, name in enumerate(tool_names[:10], 1):
        print(f"  {i}. {name}")
    
    # 查找execute_shell_command工具
    shell_tool = None
    for tool in openai_tools:
        if tool["function"]["name"] == "execute_shell_command":
            shell_tool = tool
            break
    
    if shell_tool:
        print(f"\n✅ 找到 execute_shell_command 工具!")
        print(f"描述: {shell_tool['function']['description']}")
        print(f"参数: {list(shell_tool['function']['parameters']['properties'].keys())}")
    
    assert "execute_shell_command" in tool_names
    assert len(tool_names) == 50  # 验证工具总数
    assert shell_tool is not None


def test_execute_tool_directly():
    """直接测试execute_shell_command工具"""
    print("\n=== 测试: 直接调用工具 ===")
    
    from agent.tools.mac_tools import ExecuteShellCommandTool
    
    tool = ExecuteShellCommandTool()
    
    # 测试1: 简单命令
    print("\n1. 测试简单命令")
    result = tool.execute({"command": "echo 'Test from registry'"})
    print(f"结果: {result}")
    assert result["ok"] is True
    
    # 测试2: 查看当前目录
    print("\n2. 测试pwd命令")
    result = tool.execute({"command": "pwd"})
    print(f"结果: {result}")
    assert result["ok"] is True
    
    # 测试3: 列出文件
    print("\n3. 测试ls命令")
    result = tool.execute({"command": "ls -la | head -3"})
    print(f"结果: {result}")
    assert result["ok"] is True


if __name__ == "__main__":
    print("开始测试 Agent 工具集成...")
    
    try:
        test_tool_registry()
        test_execute_tool_directly()
        
        print("\n" + "="*50)
        print("✅ 所有集成测试通过！")
        print("="*50)
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
