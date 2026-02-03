# File: backend/agent/tools/mac_tools.py
# Purpose: 主入口文件 - 从各个模块导入工具，保持向后兼容
"""
macOS工具主入口文件

此文件从各个功能模块导入所有工具，保持向后兼容性。
工具已按功能分类到以下模块：
- base_tools: 基础工具类
- system: 系统相关工具
- file: 文件管理工具
- document: 文档处理工具
- media: 媒体处理工具
- network: 网络工具
- developer: 开发者工具
- productivity: 生产力工具
- data: 数据处理工具
- text: 文本处理工具
- app: 应用管理工具
- shell: Shell命令执行工具
- time: 时间工具

所有工具已完成模块化拆分，代码结构更清晰，易于维护。
"""

from typing import Any

# 基础工具
from agent.tools.base_tools import SimpleCommandTool

# 系统工具
from agent.tools.system import (
    GetEnvironmentVariablesTool,
    SpotlightSearchTool,
    SystemInfoTool,
    TopProcessesTool,
)

# 文件工具
from agent.tools.file import (
    AppendFileTool,
    DiffTool,
    FileInfoTool,
    FindAdvancedTool,
    FindInFileTool,
    ListDirectoryTool,
    MakeDirectoryTool,
    MoveToTrashTool,
    ReadFileTool,
    SearchFilesTool,
    WriteFileTool,
)

# 文档工具
from agent.tools.document import (
    BatchSummarizeDocumentsTool,
    ExtractTextFromDocumentsTool,
)

# Shell工具
from agent.tools.shell import ExecuteShellCommandTool

# 媒体工具
from agent.tools.media import (
    CaptureScreenshotTool,
    CompressImagesTool,
    GetVideoInfoTool,
)

# 网络工具
from agent.tools.network import (
    CheckWebsiteStatusTool,
    DownloadFileTool,
    PingHostTool,
)

# 开发者工具
from agent.tools.developer import (
    GitLogTool,
    GitStatusTool,
    PortKillerTool,
    RunPythonScriptTool,
)

# 生产力工具
from agent.tools.productivity import (
    CalculateHashTool,
    ClipboardOperationsTool,
    CompressFilesTool,
    ExtractArchiveTool,
)

# 数据处理工具
from agent.tools.data import (
    CsvAnalyzerTool,
    JsonFormatterTool,
    TextStatisticsTool,
)

# 文本处理工具
from agent.tools.text import (
    GrepRecursiveTool,
    GrepSearchTool,
    TailLogTool,
)

# 应用管理工具
from agent.tools.app import (
    OpenAppTool,
    OpenUrlTool,
)

# 时间工具
from agent.tools.time import TimezoneConverterTool

# 记忆工具
from agent.tools.memory import UpdateMemoryTool

# 导入命令生成函数
from agent.tools.env_detector import (
    get_dns_info_command,
    get_network_info_command,
    get_open_ports_command,
    get_ping_command,
    get_wifi_info_command,
)


def build_default_tools() -> list[Any]:
    """构建默认工具集 - 共51个工具，覆盖工作生活的方方面面
    
    核心工具:
    - ExecuteShellCommandTool: 执行任意Shell命令（支持管道、重定向，内置安全检查）
    - UpdateMemoryTool: 更新用户记忆（偏好、事实、情景、任务、关系）
    
    高级工具:
    - GrepSearchTool: 在文件中搜索正则表达式
    - GrepRecursiveTool: 递归搜索目录
    - TailLogTool: 查看日志文件
    - FindAdvancedTool: 高级文件查找
    - DiffTool: 文件对比
    - PortKillerTool: 杀死占用端口的进程
    """
    return [
        # ============================================================
        # 系统信息与监控工具 (System Information & Monitoring)
        # ============================================================
        SystemInfoTool(),
        SimpleCommandTool(
            name="disk_usage",
            description="查看磁盘空间使用情况",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["/bin/df", "-h"],
        ),
        SimpleCommandTool(
            name="battery_status",
            description="查看电源与电池状态",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["/usr/bin/pmset", "-g", "batt"],
        ),
        SimpleCommandTool(
            name="system_sleep_settings",
            description="查看睡眠与电源策略",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["/usr/bin/pmset", "-g"],
        ),
        # ============================================================
        # 进程管理工具 (Process Management)
        # ============================================================
        SimpleCommandTool(
            name="process_list",
            description="列出当前进程",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["/bin/ps", "aux"],
        ),
        TopProcessesTool(),
        # ============================================================
        # 网络工具 (Network Tools)
        # ============================================================
        SimpleCommandTool(
            name="open_ports",
            description="列出监听端口",
            parameters={"type": "object", "properties": {}, "required": []},
            command=get_open_ports_command,
        ),
        SimpleCommandTool(
            name="network_info",
            description="获取网络接口信息",
            parameters={"type": "object", "properties": {}, "required": []},
            command=get_network_info_command,
        ),
        SimpleCommandTool(
            name="dns_info",
            description="获取 DNS 配置",
            parameters={"type": "object", "properties": {}, "required": []},
            command=get_dns_info_command,
        ),
        SimpleCommandTool(
            name="wifi_info",
            description="获取当前 Wi-Fi 连接信息",
            parameters={"type": "object", "properties": {}, "required": []},
            command=get_wifi_info_command,
        ),
        DownloadFileTool(),
        CheckWebsiteStatusTool(),
        PingHostTool(),
        # ============================================================
        # 文件管理工具 (File Management)
        # ============================================================
        ListDirectoryTool(),
        SearchFilesTool(),
        ReadFileTool(),
        WriteFileTool(),
        AppendFileTool(),
        MakeDirectoryTool(),
        FileInfoTool(),
        FindInFileTool(),
        MoveToTrashTool(),
        # ============================================================
        # 文档处理工具 (Document Processing) - 重点功能
        # ============================================================
        BatchSummarizeDocumentsTool(),  # 多线程批量文档总结 - 核心功能
        ExtractTextFromDocumentsTool(),  # 批量提取文本
        # ============================================================
        # 媒体处理工具 (Media Processing)
        # ============================================================
        CompressImagesTool(),  # 批量图片压缩
        CaptureScreenshotTool(),  # 截屏
        GetVideoInfoTool(),  # 视频信息
        # ============================================================
        # 开发者工具 (Developer Tools)
        # ============================================================
        GitStatusTool(),  # Git状态
        GitLogTool(),  # Git日志
        RunPythonScriptTool(),  # 执行Python脚本
        # ============================================================
        # 生产力工具 (Productivity Tools)
        # ============================================================
        CompressFilesTool(),  # 压缩文件
        ExtractArchiveTool(),  # 解压缩
        CalculateHashTool(),  # 计算哈希
        ClipboardOperationsTool(),  # 剪贴板操作
        # ============================================================
        # 系统管理工具 (System Management)
        # ============================================================
        GetEnvironmentVariablesTool(),  # 环境变量
        SpotlightSearchTool(),  # Spotlight搜索
        # ============================================================
        # 数据处理工具 (Data Processing)
        # ============================================================
        JsonFormatterTool(),  # JSON格式化
        CsvAnalyzerTool(),  # CSV分析
        TextStatisticsTool(),  # 文本统计
        # ============================================================
        # 时间工具 (Time Tools)
        # ============================================================
        TimezoneConverterTool(),  # 时区转换
        # ============================================================
        # 应用管理工具 (Application Management)
        # ============================================================
        OpenAppTool(),
        OpenUrlTool(),
        SimpleCommandTool(
            name="list_applications",
            description="列出 /Applications 下的应用",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["/bin/ls", "-1", "/Applications"],
        ),
        # ============================================================
        # 文本处理工具 (Text Processing) - 新增
        # ============================================================
        GrepSearchTool(),  # 在文件中搜索正则表达式
        GrepRecursiveTool(),  # 递归搜索目录
        TailLogTool(),  # 查看日志文件
        # ============================================================
        # 高级文件操作 (Advanced File Operations) - 新增
        # ============================================================
        FindAdvancedTool(),  # 高级文件查找
        DiffTool(),  # 文件对比
        # ============================================================
        # 开发者工具增强 (Developer Tools Enhanced) - 新增
        # ============================================================
        PortKillerTool(),  # 杀死占用端口的进程
        # ============================================================
        # 通用命令执行 (Universal Command Execution) - 核心功能
        # ============================================================
        ExecuteShellCommandTool(),  # 执行任意Shell命令
        # ============================================================
        # 记忆管理工具 (Memory Management) - 核心功能
        # ============================================================
        UpdateMemoryTool(),  # 更新用户记忆
    ]


# 向后兼容：导出所有工具类
__all__ = [
    # 基础工具
    "SimpleCommandTool",
    # 系统工具
    "SystemInfoTool",
    "TopProcessesTool",
    "GetEnvironmentVariablesTool",
    "SpotlightSearchTool",
    # 文件工具
    "ListDirectoryTool",
    "SearchFilesTool",
    "ReadFileTool",
    "WriteFileTool",
    "AppendFileTool",
    "MakeDirectoryTool",
    "FileInfoTool",
    "FindInFileTool",
    "MoveToTrashTool",
    "FindAdvancedTool",
    "DiffTool",
    # 文档工具
    "BatchSummarizeDocumentsTool",
    "ExtractTextFromDocumentsTool",
    # Shell工具
    "ExecuteShellCommandTool",
    # 媒体工具
    "CompressImagesTool",
    "CaptureScreenshotTool",
    "GetVideoInfoTool",
    # 网络工具
    "DownloadFileTool",
    "CheckWebsiteStatusTool",
    "PingHostTool",
    # 开发者工具
    "GitStatusTool",
    "GitLogTool",
    "RunPythonScriptTool",
    "PortKillerTool",
    # 生产力工具
    "CompressFilesTool",
    "ExtractArchiveTool",
    "CalculateHashTool",
    "ClipboardOperationsTool",
    # 数据处理工具
    "JsonFormatterTool",
    "CsvAnalyzerTool",
    "TextStatisticsTool",
    # 文本处理工具
    "GrepSearchTool",
    "GrepRecursiveTool",
    "TailLogTool",
    # 应用管理工具
    "OpenAppTool",
    "OpenUrlTool",
    # 时间工具
    "TimezoneConverterTool",
    # 记忆工具
    "UpdateMemoryTool",
    # 构建函数
    "build_default_tools",
]
