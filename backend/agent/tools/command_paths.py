# File: backend/agent/tools/command_paths.py
# Purpose: macOS系统命令路径映射，确保在各种环境下都能找到正确的命令路径
import shutil
from pathlib import Path

# 常用命令的标准路径
COMMAND_PATHS = {
    "ifconfig": "/sbin/ifconfig",
    "networksetup": "/usr/sbin/networksetup",
    "scutil": "/usr/sbin/scutil",
    "pmset": "/usr/bin/pmset",
    "lsof": "/usr/sbin/lsof",
    "mdfind": "/usr/bin/mdfind",
    "screencapture": "/usr/sbin/screencapture",
    "open": "/usr/bin/open",
    "pbpaste": "/usr/bin/pbpaste",
    "pbcopy": "/usr/bin/pbcopy",
    "ping": "/sbin/ping",
    "curl": "/usr/bin/curl",
    "git": "/usr/bin/git",
    "python3": "/usr/bin/python3",
    "df": "/bin/df",
    "ps": "/bin/ps",
    "sw_vers": "/usr/bin/sw_vers",
    "uname": "/usr/bin/uname",
    "sysctl": "/usr/sbin/sysctl",
    "ls": "/bin/ls",
    "date": "/bin/date",
    "ffprobe": "/usr/local/bin/ffprobe",
}


def resolve_command(command_name: str) -> str:
    """
    解析命令的完整路径
    优先使用预定义路径，如果不存在则尝试使用shutil.which
    
    Args:
        command_name: 命令名称或路径
        
    Returns:
        命令的完整路径，如果找不到则返回原命令名
    """
    # 如果已经是完整路径，直接返回
    if command_name.startswith("/"):
        return command_name
    
    # 尝试使用预定义路径
    if command_name in COMMAND_PATHS:
        path = COMMAND_PATHS[command_name]
        if Path(path).exists():
            return path
    
    # 尝试使用shutil.which查找
    which_path = shutil.which(command_name)
    if which_path:
        return which_path
    
    # 如果都找不到，返回原命令名（让系统尝试）
    return command_name


def resolve_command_list(command_list: list[str]) -> list[str]:
    """
    解析命令列表中第一个元素（命令名）的完整路径
    
    Args:
        command_list: 命令及参数列表，如 ["ls", "-la"]
        
    Returns:
        解析后的命令列表，如 ["/bin/ls", "-la"]
    """
    if not command_list:
        return command_list
    
    resolved = command_list.copy()
    resolved[0] = resolve_command(command_list[0])
    return resolved
