"""
File: backend/tests/test_cases_config.py
Purpose: Test cases configuration for all Mac Agent tools
Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/test_cases_config.py

【架构设计原则】【配置外置】
所有工具的测试用例配置，便于维护和扩展
"""

from pathlib import Path

# 获取测试数据目录
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_DATA_DIR.mkdir(exist_ok=True)

# 所有工具的测试用例配置
TEST_CASES = {
    # ==================== 系统信息与监控 ====================
    "system_info": [
        {
            "description": "获取系统基本信息",
            "args": {}
        }
    ],
    
    "disk_usage": [
        {
            "description": "查看磁盘空间使用情况",
            "args": {}
        }
    ],
    
    "battery_status": [
        {
            "description": "查看电池状态",
            "args": {}
        }
    ],
    
    "system_sleep_settings": [
        {
            "description": "查看系统睡眠设置",
            "args": {}
        }
    ],
    
    # ==================== 进程管理 ====================
    "process_list": [
        {
            "description": "列出所有运行中的进程",
            "args": {}
        }
    ],
    
    "top_processes": [
        {
            "description": "获取CPU使用率最高的5个进程",
            "args": {"limit": 5}
        },
        {
            "description": "获取CPU使用率最高的10个进程",
            "args": {"limit": 10}
        }
    ],
    
    "port_killer": [
        {
            "description": "查找占用8888端口的进程（测试查找功能）",
            "args": {"port": 8888, "kill": False}
        }
    ],
    
    # ==================== 网络工具 ====================
    "network_info": [
        {
            "description": "获取网络接口信息",
            "args": {}
        }
    ],
    
    "dns_info": [
        {
            "description": "获取DNS配置信息",
            "args": {}
        }
    ],
    
    "wifi_info": [
        {
            "description": "获取当前Wi-Fi连接信息",
            "args": {}
        }
    ],
    
    "open_ports": [
        {
            "description": "列出所有监听端口",
            "args": {}
        }
    ],
    
    "ping_host": [
        {
            "description": "Ping百度测试网络连接",
            "args": {"host": "baidu.com", "count": 3}
        },
        {
            "description": "Ping Google DNS",
            "args": {"host": "8.8.8.8", "count": 2}
        }
    ],
    
    "download_file": [
        {
            "description": "下载一个小文件（测试用）",
            "args": {
                "url": "https://www.baidu.com/robots.txt",
                "output_path": str(TEST_DATA_DIR / "downloaded_robots.txt")
            }
        }
    ],
    
    "check_website_status": [
        {
            "description": "检查百度网站状态",
            "args": {"url": "https://www.baidu.com"}
        }
    ],
    
    # ==================== 文件管理 ====================
    "list_directory": [
        {
            "description": "列出当前目录内容",
            "args": {"path": "."}
        },
        {
            "description": "列出测试数据目录",
            "args": {"path": str(TEST_DATA_DIR)}
        }
    ],
    
    "search_files": [
        {
            "description": "搜索Python文件",
            "args": {"pattern": "*.py", "path": "."}
        },
        {
            "description": "搜索Markdown文件",
            "args": {"pattern": "*.md", "path": "."}
        }
    ],
    
    "read_file": [
        {
            "description": "读取README文件",
            "args": {"path": "README.md", "max_bytes": 1000}
        }
    ],
    
    "write_file": [
        {
            "description": "写入测试文件",
            "args": {
                "path": str(TEST_DATA_DIR / "test_write.txt"),
                "content": "This is a test file created by Mac Agent.\n测试中文内容。",
                "overwrite": True
            }
        }
    ],
    
    "append_file": [
        {
            "description": "追加内容到测试文件",
            "args": {
                "path": str(TEST_DATA_DIR / "test_append.txt"),
                "content": "Appended line 1\n",
                "create_if_missing": True
            }
        }
    ],
    
    "make_directory": [
        {
            "description": "创建测试目录",
            "args": {"path": str(TEST_DATA_DIR / "test_subdir")}
        }
    ],
    
    "file_info": [
        {
            "description": "获取README文件信息",
            "args": {"path": "README.md"}
        }
    ],
    
    "find_in_file": [
        {
            "description": "在README中查找关键词",
            "args": {"path": "README.md", "query": "Agent"}
        }
    ],
    
    "move_to_trash": [
        {
            "description": "移动测试文件到回收站",
            "args": {"path": str(TEST_DATA_DIR / "test_trash.txt")}
        }
    ],
    
    "find_advanced": [
        {
            "description": "查找大于1KB的Python文件",
            "args": {
                "directory": ".",
                "name_pattern": "*.py",
                "min_size_kb": 1
            }
        }
    ],
    
    # ==================== Shell命令 ====================
    "execute_shell_command": [
        {
            "description": "执行简单命令：查看当前目录",
            "args": {"command": "pwd"}
        },
        {
            "description": "执行管道命令：统计Python文件数量",
            "args": {"command": "find . -name '*.py' | wc -l"}
        },
        {
            "description": "测试危险命令拦截（预期失败）",
            "args": {"command": "rm -rf /"},
            "expect_failure": True
        }
    ],
    
    "grep_search": [
        {
            "description": "在文件中搜索关键词",
            "args": {"pattern": "Agent", "file_path": "README.md"}
        }
    ],
    
    "grep_recursive": [
        {
            "description": "递归搜索Python文件中的import语句",
            "args": {"pattern": "import", "directory": ".", "file_pattern": "*.py"}
        }
    ],
    
    "tail_log": [
        {
            "description": "查看README最后10行",
            "args": {"file_path": "README.md", "lines": 10}
        }
    ],
    
    "diff_files": [
        {
            "description": "对比两个文件",
            "args": {
                "path1": str(TEST_DATA_DIR / "file1.txt"),
                "path2": str(TEST_DATA_DIR / "file2.txt")
            }
        }
    ],
    
    # ==================== 压缩与归档 ====================
    "compress_files": [
        {
            "description": "压缩测试数据目录",
            "args": {
                "source_paths": [str(TEST_DATA_DIR / "test_write.txt")],
                "output_zip": str(TEST_DATA_DIR / "test_archive.zip")
            }
        }
    ],
    
    "extract_archive": [
        {
            "description": "解压缩测试文件",
            "args": {
                "archive_path": str(TEST_DATA_DIR / "test_archive.zip"),
                "output_directory": str(TEST_DATA_DIR / "extracted")
            }
        }
    ],
    
    "calculate_hash": [
        {
            "description": "计算README的MD5哈希",
            "args": {"file_path": "README.md", "algorithm": "md5"}
        },
        {
            "description": "计算README的SHA256哈希",
            "args": {"file_path": "README.md", "algorithm": "sha256"}
        }
    ],
    
    # ==================== 剪贴板与系统 ====================
    "clipboard_operations": [
        {
            "description": "写入剪贴板",
            "args": {"operation": "write", "content": "Mac Agent Test Content"}
        },
        {
            "description": "读取剪贴板",
            "args": {"operation": "read"}
        }
    ],
    
    "get_environment_variables": [
        {
            "description": "获取所有环境变量",
            "args": {}
        },
        {
            "description": "获取PATH环境变量",
            "args": {"variable_name": "PATH"}
        }
    ],
    
    "spotlight_search": [
        {
            "description": "使用Spotlight搜索Python文件",
            "args": {"query": "*.py", "limit": 5}
        }
    ],
    
    # ==================== 数据处理 ====================
    "json_formatter": [
        {
            "description": "格式化JSON数据",
            "args": {
                "json_string": '{"name":"test","value":123}',
                "operation": "format"
            }
        },
        {
            "description": "压缩JSON数据",
            "args": {
                "json_string": '{\n  "name": "test",\n  "value": 123\n}',
                "operation": "minify"
            }
        }
    ],
    
    "csv_analyzer": [
        {
            "description": "分析CSV文件",
            "args": {"csv_path": str(TEST_DATA_DIR / "test_data.csv")}
        }
    ],
    
    "text_statistics": [
        {
            "description": "分析README文本统计",
            "args": {"file_path": "README.md"}
        }
    ],
    
    # ==================== 开发者工具 ====================
    "git_status": [
        {
            "description": "查询Git仓库状态",
            "args": {"repo_path": "."}
        }
    ],
    
    "git_log": [
        {
            "description": "查看最近5条Git提交",
            "args": {"repo_path": ".", "limit": 5}
        }
    ],
    
    "run_python_script": [
        {
            "description": "运行简单Python脚本",
            "args": {
                "script_path": str(TEST_DATA_DIR / "test_script.py"),
                "args": []
            }
        }
    ],
    
    # ==================== 时间工具 ====================
    "timezone_converter": [
        {
            "description": "转换时间到纽约时区",
            "args": {
                "time_str": "2026-01-29 12:00:00",
                "from_tz": "Asia/Shanghai",
                "to_tz": "America/New_York"
            }
        }
    ],
    
    # ==================== 应用管理 ====================
    "open_app": [
        {
            "description": "打开计算器应用（测试）",
            "args": {"app_name": "Calculator"}
        }
    ],
    
    "open_url": [
        {
            "description": "在浏览器打开URL",
            "args": {"url": "https://www.baidu.com"}
        }
    ],
    
    "list_applications": [
        {
            "description": "列出所有应用程序",
            "args": {}
        }
    ],
    
    # ==================== 文档处理 ====================
    "batch_summarize_documents": [
        {
            "description": "批量总结文档",
            "args": {
                "file_paths": [str(TEST_DATA_DIR / "test_write.txt")],
                "output_path": str(TEST_DATA_DIR / "summaries.md")
            }
        }
    ],
    
    "extract_text_from_documents": [
        {
            "description": "从文档提取文本",
            "args": {
                "file_paths": [str(TEST_DATA_DIR / "test_write.txt")],
                "output_directory": str(TEST_DATA_DIR / "extracted_text")
            }
        }
    ],
    
    # ==================== 媒体处理 ====================
    "compress_images": [
        {
            "description": "压缩图片（需要PIL库和图片文件，预期可能失败）",
            "args": {
                "image_paths": [str(TEST_DATA_DIR / "test_image.jpg")],
                "output_directory": str(TEST_DATA_DIR / "compressed_images"),
                "quality": 80
            },
            "expect_failure": True
        }
    ],
    
    "capture_screenshot": [
        {
            "description": "捕获全屏截图",
            "args": {
                "output_path": str(TEST_DATA_DIR / "screenshot.png"),
                "region": None
            }
        }
    ],
    
    "get_video_info": [
        {
            "description": "获取视频信息（需要视频文件，预期可能失败）",
            "args": {"video_path": str(TEST_DATA_DIR / "test_video.mp4")},
            "expect_failure": True
        }
    ],
}


def get_all_test_cases():
    """获取所有测试用例"""
    return TEST_CASES


def get_test_cases_by_tool(tool_name: str):
    """获取指定工具的测试用例"""
    return TEST_CASES.get(tool_name, [])


def get_tools_count():
    """获取工具总数"""
    return len(TEST_CASES)


def get_test_cases_count():
    """获取测试用例总数"""
    return sum(len(cases) for cases in TEST_CASES.values())
