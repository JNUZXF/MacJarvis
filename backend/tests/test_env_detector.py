#!/usr/bin/env python3
# File: backend/tests/test_env_detector.py
# Purpose: 测试环境检测和命令适配功能
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.tools.env_detector import (
    is_macos,
    is_linux,
    is_docker,
    get_network_info_command,
    get_dns_info_command,
    get_wifi_info_command,
    get_open_ports_command,
    get_ping_command,
    get_environment_info,
)


def test_env_detection():
    """测试环境检测"""
    print("=" * 80)
    print("环境检测测试")
    print("=" * 80)
    
    env_info = get_environment_info()
    print(f"\n环境信息:")
    for key, value in env_info.items():
        print(f"  {key}: {value}")
    
    print(f"\n平台检测:")
    print(f"  is_macos(): {is_macos()}")
    print(f"  is_linux(): {is_linux()}")
    print(f"  is_docker(): {is_docker()}")
    
    print(f"\n命令适配:")
    print(f"  network_info: {get_network_info_command()}")
    print(f"  dns_info: {get_dns_info_command()}")
    print(f"  wifi_info: {get_wifi_info_command()}")
    print(f"  open_ports: {get_open_ports_command()}")
    print(f"  ping: {get_ping_command()}")
    
    # 测试命令是否存在
    print(f"\n命令可用性检查:")
    from agent.tools.command_runner import CommandRunner
    
    runner = CommandRunner(timeout_s=5)
    
    # 测试网络信息命令
    network_cmd = get_network_info_command()
    result = runner.run(network_cmd)
    if result["ok"]:
        print(f"  ✓ {network_cmd[0]} 可用")
        print(f"    输出长度: {len(result.get('stdout', ''))} 字符")
    else:
        print(f"  ✗ {network_cmd[0]} 不可用: {result.get('error', 'Unknown')}")
    
    # 测试DNS命令
    dns_cmd = get_dns_info_command()
    result = runner.run(dns_cmd)
    if result["ok"]:
        print(f"  ✓ {dns_cmd[0]} 可用")
        print(f"    输出长度: {len(result.get('stdout', ''))} 字符")
    else:
        print(f"  ✗ {dns_cmd[0]} 不可用: {result.get('error', 'Unknown')}")
    
    # 测试ping命令
    ping_cmd = get_ping_command()
    result = runner.run(ping_cmd + ["-c", "1", "127.0.0.1"])
    if result["ok"]:
        print(f"  ✓ {ping_cmd[0]} 可用")
    else:
        print(f"  ✗ {ping_cmd[0]} 不可用: {result.get('error', 'Unknown')}")


if __name__ == "__main__":
    test_env_detection()
