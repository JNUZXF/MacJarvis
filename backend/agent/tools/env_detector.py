# File: backend/agent/tools/env_detector.py
# Purpose: 检测运行环境（macOS/Linux/Docker），提供环境适配功能
import os
import platform
import subprocess
from pathlib import Path


def is_macos() -> bool:
    """检测是否在macOS上运行"""
    return platform.system() == "Darwin"


def is_linux() -> bool:
    """检测是否在Linux上运行"""
    return platform.system() == "Linux"


def is_docker() -> bool:
    """检测是否在Docker容器中运行"""
    # 方法1: 检查 /.dockerenv 文件
    if Path("/.dockerenv").exists():
        return True
    
    # 方法2: 检查 /proc/self/cgroup 是否包含docker
    try:
        with open("/proc/self/cgroup", "r") as f:
            content = f.read()
            if "docker" in content:
                return True
    except (FileNotFoundError, PermissionError):
        pass
    
    # 方法3: 检查环境变量
    if os.environ.get("container") == "docker":
        return True
    
    return False


def get_network_info_command() -> list[str]:
    """获取网络接口信息命令（跨平台）"""
    if is_macos():
        return ["/sbin/ifconfig"]
    elif is_linux():
        # Linux使用ip命令
        return ["/sbin/ip", "addr", "show"]
    else:
        # 回退到hostname
        return ["hostname", "-I"]


def get_dns_info_command() -> list[str]:
    """获取DNS配置命令（跨平台）"""
    if is_macos():
        return ["/usr/sbin/scutil", "--dns"]
    elif is_linux():
        # Linux读取/etc/resolv.conf
        return ["cat", "/etc/resolv.conf"]
    else:
        return ["cat", "/etc/resolv.conf"]


def get_wifi_info_command() -> list[str]:
    """获取WiFi信息命令（跨平台）"""
    if is_macos():
        return ["/usr/sbin/networksetup", "-getairportnetwork", "en0"]
    elif is_linux():
        # Linux使用iwconfig或nmcli
        # 先尝试iwconfig
        if Path("/sbin/iwconfig").exists():
            return ["/sbin/iwconfig"]
        elif Path("/usr/bin/nmcli").exists():
            return ["/usr/bin/nmcli", "device", "wifi", "list"]
        else:
            # 回退到ip link
            return ["/sbin/ip", "link", "show"]
    else:
        return ["/sbin/ip", "link", "show"]


def get_open_ports_command() -> list[str]:
    """获取监听端口命令（跨平台）"""
    if is_macos():
        return ["/usr/sbin/lsof", "-nP", "-iTCP", "-sTCP:LISTEN"]
    elif is_linux():
        # Linux使用netstat或ss
        if Path("/bin/ss").exists():
            return ["/bin/ss", "-tlnp"]
        elif Path("/bin/netstat").exists():
            return ["/bin/netstat", "-tlnp"]
        else:
            return ["/bin/ss", "-tlnp"]
    else:
        return ["/bin/ss", "-tlnp"]


def get_ping_command() -> list[str]:
    """获取ping命令（跨平台）"""
    if is_macos():
        return ["/sbin/ping"]
    elif is_linux():
        return ["/bin/ping"]
    else:
        return ["ping"]


def get_environment_info() -> dict:
    """获取环境信息"""
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "is_macos": is_macos(),
        "is_linux": is_linux(),
        "is_docker": is_docker(),
        "architecture": platform.machine(),
    }
