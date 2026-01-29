"""
File: backend/tests/test_shell_command.py
Purpose: Test the new ExecuteShellCommandTool
Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/test_shell_command.py
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent.tools.mac_tools import ExecuteShellCommandTool


def test_simple_command():
    """测试简单命令"""
    print("\n=== 测试1: 简单命令 ===")
    tool = ExecuteShellCommandTool()
    result = tool.execute({"command": "echo 'Hello, Mac Agent!'"})
    print(f"结果: {result}")
    assert result["ok"] is True
    assert "Hello, Mac Agent!" in result["stdout"]


def test_pipe_command():
    """测试管道命令"""
    print("\n=== 测试2: 管道命令 ===")
    tool = ExecuteShellCommandTool()
    result = tool.execute({"command": "echo 'line1\nline2\nline3' | grep 'line2'"})
    print(f"结果: {result}")
    assert result["ok"] is True
    assert "line2" in result["stdout"]


def test_working_directory():
    """测试工作目录"""
    print("\n=== 测试3: 工作目录 ===")
    tool = ExecuteShellCommandTool()
    # 使用当前目录，这是允许的
    import os
    cwd = os.getcwd()
    result = tool.execute({
        "command": "pwd",
        "working_directory": cwd
    })
    print(f"结果: {result}")
    assert result["ok"] is True
    assert cwd in result["stdout"]


def test_dangerous_command():
    """测试危险命令拦截"""
    print("\n=== 测试4: 危险命令拦截 ===")
    tool = ExecuteShellCommandTool()
    
    dangerous_commands = [
        "rm -rf /",
        "rm -rf /*",
        "mkfs.ext4 /dev/sda1",
    ]
    
    for cmd in dangerous_commands:
        result = tool.execute({"command": cmd})
        print(f"命令: {cmd}")
        print(f"结果: {result}")
        assert result["ok"] is False
        assert "危险命令被拒绝" in result["error"]


def test_timeout():
    """测试超时"""
    print("\n=== 测试5: 超时控制 ===")
    tool = ExecuteShellCommandTool()
    result = tool.execute({
        "command": "sleep 5",
        "timeout": 2
    })
    print(f"结果: {result}")
    assert result["ok"] is False
    assert "超时" in result["error"]


def test_command_with_variables():
    """测试带变量的命令"""
    print("\n=== 测试6: 环境变量 ===")
    tool = ExecuteShellCommandTool()
    result = tool.execute({"command": "echo $HOME"})
    print(f"结果: {result}")
    assert result["ok"] is True
    assert len(result["stdout"]) > 0


if __name__ == "__main__":
    print("开始测试 ExecuteShellCommandTool...")
    
    try:
        test_simple_command()
        test_pipe_command()
        test_working_directory()
        test_dangerous_command()
        test_timeout()
        test_command_with_variables()
        
        print("\n" + "="*50)
        print("✅ 所有测试通过！")
        print("="*50)
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
