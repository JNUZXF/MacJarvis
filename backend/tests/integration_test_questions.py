# File: backend/tests/integration_test_questions.py
# Purpose: 集成测试问题集，用于测试智能体在真实对话中的工具调用能力
"""
集成测试问题集
覆盖所有47个工具的真实使用场景
"""

TEST_QUESTIONS = [
    # ============================================================================
    # 系统信息类 (System Information)
    # ============================================================================
    {
        "id": "sys_001",
        "question": "查看系统版本信息",
        "expected_tools": ["system_info"],
        "category": "system_info",
        "description": "获取macOS版本、内核信息和硬件概览"
    },
    {
        "id": "sys_002",
        "question": "查看磁盘使用情况",
        "expected_tools": ["disk_usage"],
        "category": "system_info",
        "description": "查看所有磁盘的空间使用情况"
    },
    {
        "id": "sys_003",
        "question": "查看电池状态",
        "expected_tools": ["battery_status"],
        "category": "system_info",
        "description": "查看电池健康度和电源设置"
    },
    {
        "id": "sys_004",
        "question": "查看睡眠和电源策略",
        "expected_tools": ["system_sleep_settings"],
        "category": "system_info",
        "description": "查看系统睡眠和电源管理设置"
    },
    
    # ============================================================================
    # 进程管理类 (Process Management)
    # ============================================================================
    {
        "id": "proc_001",
        "question": "列出所有正在运行的进程",
        "expected_tools": ["process_list"],
        "category": "process",
        "description": "查看系统中所有进程的详细信息"
    },
    {
        "id": "proc_002",
        "question": "查看CPU占用最高的10个进程",
        "expected_tools": ["top_processes"],
        "category": "process",
        "description": "按CPU使用率排序显示前10个进程"
    },
    {
        "id": "proc_003",
        "question": "哪些进程占用CPU最多？",
        "expected_tools": ["top_processes"],
        "category": "process",
        "description": "自然语言查询CPU占用情况"
    },
    
    # ============================================================================
    # 网络工具类 (Network Tools)
    # ============================================================================
    {
        "id": "net_001",
        "question": "查看网络接口配置",
        "expected_tools": ["network_info"],
        "category": "network",
        "description": "查看所有网络接口的IP地址和配置"
    },
    {
        "id": "net_002",
        "question": "查看当前WiFi连接",
        "expected_tools": ["wifi_info"],
        "category": "network",
        "description": "查看当前连接的WiFi网络名称"
    },
    {
        "id": "net_003",
        "question": "查看DNS配置",
        "expected_tools": ["dns_info"],
        "category": "network",
        "description": "查看系统DNS服务器配置"
    },
    {
        "id": "net_004",
        "question": "查看监听的端口",
        "expected_tools": ["open_ports"],
        "category": "network",
        "description": "查看系统中正在监听的TCP端口"
    },
    {
        "id": "net_005",
        "question": "ping一下google.com",
        "expected_tools": ["ping_host"],
        "category": "network",
        "description": "测试到google.com的网络连接"
    },
    {
        "id": "net_006",
        "question": "测试到百度的网络连接",
        "expected_tools": ["ping_host"],
        "category": "network",
        "description": "ping baidu.com测试网络"
    },
    {
        "id": "net_007",
        "question": "检查github.com是否可访问",
        "expected_tools": ["check_website_status"],
        "category": "network",
        "description": "检查网站HTTP状态码"
    },
    
    # ============================================================================
    # 文件操作类 (File Operations)
    # ============================================================================
    {
        "id": "file_001",
        "question": "列出桌面上的文件",
        "expected_tools": ["list_directory"],
        "category": "file_ops",
        "description": "查看桌面目录内容"
    },
    {
        "id": "file_002",
        "question": "在桌面创建一个test.txt文件，内容是'Hello World'",
        "expected_tools": ["write_file"],
        "category": "file_ops",
        "description": "创建新文件并写入内容"
    },
    {
        "id": "file_003",
        "question": "读取桌面上的test.txt文件内容",
        "expected_tools": ["read_file"],
        "category": "file_ops",
        "description": "读取文件内容"
    },
    {
        "id": "file_004",
        "question": "在test.txt文件末尾追加一行'New Line'",
        "expected_tools": ["append_file"],
        "category": "file_ops",
        "description": "追加内容到文件"
    },
    {
        "id": "file_005",
        "question": "在桌面创建一个名为test_folder的文件夹",
        "expected_tools": ["make_directory"],
        "category": "file_ops",
        "description": "创建新目录"
    },
    {
        "id": "file_006",
        "question": "查看test.txt文件的详细信息",
        "expected_tools": ["file_info"],
        "category": "file_ops",
        "description": "获取文件大小、修改时间等信息"
    },
    {
        "id": "file_007",
        "question": "在桌面搜索所有txt文件",
        "expected_tools": ["search_files"],
        "category": "file_ops",
        "description": "按文件名模式搜索文件"
    },
    {
        "id": "file_008",
        "question": "在test.txt文件中搜索包含'Hello'的行",
        "expected_tools": ["find_in_file"],
        "category": "file_ops",
        "description": "在文件中搜索文本内容"
    },
    {
        "id": "file_009",
        "question": "将test.txt文件移动到回收站",
        "expected_tools": ["move_to_trash"],
        "category": "file_ops",
        "description": "安全删除文件"
    },
    
    # ============================================================================
    # 应用管理类 (Application Management)
    # ============================================================================
    {
        "id": "app_001",
        "question": "列出所有已安装的应用",
        "expected_tools": ["list_applications"],
        "category": "apps",
        "description": "查看/Applications目录下的应用"
    },
    {
        "id": "app_002",
        "question": "打开Safari浏览器",
        "expected_tools": ["open_app"],
        "category": "apps",
        "description": "启动指定应用程序"
    },
    {
        "id": "app_003",
        "question": "在浏览器中打开https://www.apple.com",
        "expected_tools": ["open_url"],
        "category": "apps",
        "description": "在默认浏览器中打开URL"
    },
    
    # ============================================================================
    # 开发者工具类 (Developer Tools)
    # ============================================================================
    {
        "id": "dev_001",
        "question": "查看当前目录的git状态",
        "expected_tools": ["git_status"],
        "category": "developer",
        "description": "查看git仓库的当前状态"
    },
    {
        "id": "dev_002",
        "question": "查看最近10条git提交记录",
        "expected_tools": ["git_log"],
        "category": "developer",
        "description": "查看git提交历史"
    },
    
    # ============================================================================
    # 生产力工具类 (Productivity Tools)
    # ============================================================================
    {
        "id": "prod_001",
        "question": "将桌面上的test文件夹压缩为test.zip",
        "expected_tools": ["compress_files"],
        "category": "productivity",
        "description": "压缩文件或目录"
    },
    {
        "id": "prod_002",
        "question": "解压test.zip到桌面",
        "expected_tools": ["extract_archive"],
        "category": "productivity",
        "description": "解压ZIP文件"
    },
    {
        "id": "prod_003",
        "question": "计算test.txt文件的MD5哈希值",
        "expected_tools": ["calculate_hash"],
        "category": "productivity",
        "description": "计算文件哈希"
    },
    {
        "id": "prod_004",
        "question": "将'Hello Clipboard'复制到剪贴板",
        "expected_tools": ["clipboard_operations"],
        "category": "productivity",
        "description": "写入剪贴板"
    },
    {
        "id": "prod_005",
        "question": "读取剪贴板内容",
        "expected_tools": ["clipboard_operations"],
        "category": "productivity",
        "description": "读取剪贴板"
    },
    
    # ============================================================================
    # 系统管理工具类 (System Management)
    # ============================================================================
    {
        "id": "mgmt_001",
        "question": "查看PATH环境变量",
        "expected_tools": ["get_environment_variables"],
        "category": "system_management",
        "description": "获取特定环境变量"
    },
    {
        "id": "mgmt_002",
        "question": "查看所有环境变量",
        "expected_tools": ["get_environment_variables"],
        "category": "system_management",
        "description": "获取所有环境变量"
    },
    {
        "id": "mgmt_003",
        "question": "使用Spotlight搜索'Safari'",
        "expected_tools": ["spotlight_search"],
        "category": "system_management",
        "description": "使用macOS Spotlight搜索"
    },
    
    # ============================================================================
    # 数据处理工具类 (Data Processing)
    # ============================================================================
    {
        "id": "data_001",
        "question": "格式化这段JSON: {\"name\":\"test\",\"value\":123}",
        "expected_tools": ["json_formatter"],
        "category": "data_processing",
        "description": "美化JSON格式"
    },
    {
        "id": "data_002",
        "question": "分析桌面上的data.csv文件",
        "expected_tools": ["csv_analyzer"],
        "category": "data_processing",
        "description": "分析CSV文件统计信息"
    },
    {
        "id": "data_003",
        "question": "统计test.txt文件的字数和行数",
        "expected_tools": ["text_statistics"],
        "category": "data_processing",
        "description": "文本统计分析"
    },
    
    # ============================================================================
    # 媒体处理工具类 (Media Processing)
    # ============================================================================
    {
        "id": "media_001",
        "question": "压缩桌面上的image.jpg图片",
        "expected_tools": ["compress_images"],
        "category": "media",
        "description": "批量压缩图片"
    },
    {
        "id": "media_002",
        "question": "截取当前屏幕并保存到桌面",
        "expected_tools": ["capture_screenshot"],
        "category": "media",
        "description": "屏幕截图"
    },
    {
        "id": "media_003",
        "question": "获取video.mp4的视频信息",
        "expected_tools": ["get_video_info"],
        "category": "media",
        "description": "查看视频文件信息"
    },
    
    # ============================================================================
    # 文档处理工具类 (Document Processing)
    # ============================================================================
    {
        "id": "doc_001",
        "question": "总结桌面上的report.pdf文档",
        "expected_tools": ["batch_summarize_documents"],
        "category": "document",
        "description": "批量总结文档"
    },
    {
        "id": "doc_002",
        "question": "从document.docx中提取文本",
        "expected_tools": ["extract_text_from_documents"],
        "category": "document",
        "description": "提取文档文本内容"
    },
    
    # ============================================================================
    # 时间工具类 (Time Tools)
    # ============================================================================
    {
        "id": "time_001",
        "question": "查看当前UTC时间",
        "expected_tools": ["timezone_converter"],
        "category": "time",
        "description": "时区转换"
    },
    {
        "id": "time_002",
        "question": "将当前时间转换为纽约时区",
        "expected_tools": ["timezone_converter"],
        "category": "time",
        "description": "转换到特定时区"
    },
    
    # ============================================================================
    # 复杂场景测试 (Complex Scenarios)
    # ============================================================================
    {
        "id": "complex_001",
        "question": "帮我检查系统状态：查看CPU占用、磁盘空间和网络连接",
        "expected_tools": ["top_processes", "disk_usage", "network_info"],
        "category": "complex",
        "description": "多工具组合使用"
    },
    {
        "id": "complex_002",
        "question": "在桌面创建一个项目文件夹，里面创建README.md文件，内容是项目说明",
        "expected_tools": ["make_directory", "write_file"],
        "category": "complex",
        "description": "多步骤文件操作"
    },
    {
        "id": "complex_003",
        "question": "搜索桌面上所有txt文件，并统计第一个文件的字数",
        "expected_tools": ["search_files", "text_statistics"],
        "category": "complex",
        "description": "搜索后处理"
    },
]


# 按类别分组
def get_questions_by_category(category: str) -> list[dict]:
    """获取指定类别的测试问题"""
    return [q for q in TEST_QUESTIONS if q["category"] == category]


# 获取所有类别
def get_all_categories() -> list[str]:
    """获取所有问题类别"""
    categories = set(q["category"] for q in TEST_QUESTIONS)
    return sorted(categories)


# 统计信息
def get_statistics() -> dict:
    """获取测试问题统计信息"""
    categories = {}
    for q in TEST_QUESTIONS:
        cat = q["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    return {
        "total_questions": len(TEST_QUESTIONS),
        "total_categories": len(categories),
        "questions_by_category": categories,
        "tools_covered": len(set(
            tool 
            for q in TEST_QUESTIONS 
            for tool in q["expected_tools"]
        ))
    }


if __name__ == "__main__":
    # 打印统计信息
    stats = get_statistics()
    print("=" * 80)
    print("集成测试问题集统计")
    print("=" * 80)
    print(f"总问题数: {stats['total_questions']}")
    print(f"总类别数: {stats['total_categories']}")
    print(f"覆盖工具数: {stats['tools_covered']}")
    print("\n各类别问题数:")
    for cat, count in sorted(stats['questions_by_category'].items()):
        print(f"  {cat}: {count}")
    
    print("\n所有测试问题:")
    for q in TEST_QUESTIONS:
        print(f"  [{q['id']}] {q['question']}")
        print(f"      工具: {', '.join(q['expected_tools'])}")
        print(f"      类别: {q['category']}")
        print()
