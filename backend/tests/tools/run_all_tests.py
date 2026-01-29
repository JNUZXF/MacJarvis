#!/usr/bin/env python3
"""
File: backend/tests/tools/run_all_tests.py
Purpose: Main test runner for all Mac Agent tools
Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/tools/run_all_tests.py

【架构设计原则】【测试策略】
运行所有工具测试，生成详细的测试报告
"""

import sys
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.tools.base import TestRunner, load_env

# 导入所有测试类
from tests.tools.system.test_system_info import (
    TestSystemInfo,
    TestDiskUsage,
    TestBatteryStatus,
    TestTopProcesses,
)
from tests.tools.file.test_file_operations import (
    TestListDirectory,
    TestReadFile,
    TestWriteFile,
    TestFileInfo,
    TestSearchFiles,
)
from tests.tools.text.test_shell_command import (
    TestExecuteShellCommand,
    TestGrepSearch,
    TestTailLog,
)
from tests.tools.network.test_network_tools import (
    TestNetworkInfo,
    TestPingHost,
    TestCheckWebsiteStatus,
)
from tests.tools.productivity.test_productivity_tools import (
    TestClipboardOperations,
    TestCalculateHash,
    TestCompressFiles,
    TestExtractArchive,
)


def main():
    """主测试函数"""
    # 加载环境变量
    load_env()
    
    # 创建测试运行器
    runner = TestRunner()
    
    print("\n" + "="*80)
    print("Mac Agent 工具全面测试")
    print("="*80)
    print("\n📋 测试计划:")
    print("  1. 系统信息工具 (4个)")
    print("  2. 文件操作工具 (5个)")
    print("  3. Shell命令工具 (3个)")
    print("  4. 网络工具 (3个)")
    print("  5. 生产力工具 (4个)")
    print("  总计: 19个工具")
    print("="*80)
    
    # 注册所有测试
    # 系统信息工具
    runner.register_test(TestSystemInfo())
    runner.register_test(TestDiskUsage())
    runner.register_test(TestBatteryStatus())
    runner.register_test(TestTopProcesses())
    
    # 文件操作工具
    runner.register_test(TestListDirectory())
    runner.register_test(TestReadFile())
    runner.register_test(TestWriteFile())
    runner.register_test(TestFileInfo())
    runner.register_test(TestSearchFiles())
    
    # Shell命令工具
    runner.register_test(TestExecuteShellCommand())
    runner.register_test(TestGrepSearch())
    runner.register_test(TestTailLog())
    
    # 网络工具
    runner.register_test(TestNetworkInfo())
    runner.register_test(TestPingHost())
    runner.register_test(TestCheckWebsiteStatus())
    
    # 生产力工具
    runner.register_test(TestClipboardOperations())
    runner.register_test(TestCalculateHash())
    runner.register_test(TestCompressFiles())
    runner.register_test(TestExtractArchive())
    
    # 运行所有测试
    runner.run_all()
    
    # 返回退出码
    return 0 if runner.results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
