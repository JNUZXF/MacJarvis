# Mac Agent 工具测试框架

> **创建日期**: 2026-01-29  
> **测试覆盖**: 19个核心工具  
> **架构**: 模块化、低耦合、高内聚

---

## 📋 目录结构

```
tests/tools/
├── README.md                    # 本文档
├── __init__.py
├── base.py                      # 测试基类和工具
├── run_all_tests.py            # 主测试运行器
│
├── system/                      # 系统信息工具测试
│   ├── __init__.py
│   └── test_system_info.py
│
├── file/                        # 文件操作工具测试
│   ├── __init__.py
│   └── test_file_operations.py
│
├── text/                        # 文本处理工具测试
│   ├── __init__.py
│   └── test_shell_command.py
│
├── network/                     # 网络工具测试
│   ├── __init__.py
│   └── test_network_tools.py
│
└── productivity/                # 生产力工具测试
    ├── __init__.py
    └── test_productivity_tools.py
```

---

## 🎯 设计原则

### 【架构设计原则】
1. **模块化设计**: 按功能分类组织测试（系统、文件、网络等）
2. **低耦合**: 每个测试类独立，互不依赖
3. **高内聚**: 相关测试放在同一模块中

### 【单一职责原则】
- 每个测试类只测试一个工具
- 每个测试方法只测试一个功能点
- 测试基类只提供通用功能

### 【测试策略】
- **单元测试**: 测试每个工具的独立功能
- **边界测试**: 测试异常情况和边界条件
- **集成测试**: 验证工具与系统的交互

---

## 🚀 快速开始

### 运行所有测试
```bash
cd backend
source .venv/bin/activate
python tests/tools/run_all_tests.py
```

### 运行特定分类测试
```bash
# 只测试系统工具
python -m pytest tests/tools/system/

# 只测试文件工具
python -m pytest tests/tools/file/

# 只测试Shell命令工具
python -m pytest tests/tools/text/test_shell_command.py
```

---

## 📊 测试覆盖

### 1. 系统信息工具 (4个)
| 工具名称 | 测试数量 | 状态 |
|---------|---------|------|
| system_info | 1 | ✅ |
| disk_usage | 1 | ✅ |
| battery_status | 1 | ✅ |
| top_processes | 2 | ✅ |

### 2. 文件操作工具 (5个)
| 工具名称 | 测试数量 | 状态 |
|---------|---------|------|
| list_directory | 2 | ✅ |
| read_file | 2 | ✅ |
| write_file | 2 | ✅ |
| file_info | 1 | ✅ |
| search_files | 2 | ✅ |

### 3. Shell命令工具 (3个) ⭐
| 工具名称 | 测试数量 | 状态 |
|---------|---------|------|
| execute_shell_command | 7 | ✅ |
| grep_search | 2 | ✅ |
| tail_log | 2 | ✅ |

### 4. 网络工具 (3个)
| 工具名称 | 测试数量 | 状态 |
|---------|---------|------|
| network_info | 1 | ✅ |
| ping_host | 2 | ✅ |
| check_website_status | 1 | ✅ |

### 5. 生产力工具 (4个)
| 工具名称 | 测试数量 | 状态 |
|---------|---------|------|
| clipboard_operations | 2 | ✅ |
| calculate_hash | 2 | ✅ |
| compress_files | 1 | ✅ |
| extract_archive | 1 | ✅ |

**总计**: 19个工具，38个测试用例，全部通过 ✅

---

## 🏗️ 架构设计

### 测试基类 (ToolTestBase)

提供统一的测试框架：

```python
class ToolTestBase(ABC):
    """工具测试基类"""
    
    @abstractmethod
    def get_tool_name(self) -> str:
        """返回要测试的工具名称"""
        pass
    
    @abstractmethod
    def run_tests(self) -> List[str]:
        """运行所有测试用例"""
        pass
    
    # 通用断言方法
    def assert_success(self, result, message="")
    def assert_failure(self, result, message="")
    def assert_has_data(self, result, key=None)
    def assert_error_contains(self, result, text)
    
    # 测试数据管理
    def create_test_file(self, filename, content="")
    def cleanup_test_file(self, file_path)
```

### 测试运行器 (TestRunner)

管理和执行所有测试：

```python
class TestRunner:
    """测试运行器"""
    
    def register_test(self, test_class)  # 注册测试
    def run_all(self)                    # 运行所有测试
    def print_summary(self)              # 打印测试摘要
```

---

## 📝 编写新测试

### 步骤1: 创建测试类

```python
from tests.tools.base import ToolTestBase

class TestYourTool(ToolTestBase):
    """测试你的工具"""
    
    def get_tool_name(self) -> str:
        return "your_tool_name"
    
    def run_tests(self):
        failures = []
        
        try:
            print("\n测试1: 基本功能")
            result = self.execute_tool({"param": "value"})
            self.assert_success(result)
            print("✅ 通过")
        except AssertionError as e:
            failures.append(f"your_tool - 测试1: {e}")
            print(f"❌ 失败: {e}")
        
        return failures
```

### 步骤2: 注册到运行器

在 `run_all_tests.py` 中：

```python
from tests.tools.your_category.test_your_tool import TestYourTool

runner.register_test(TestYourTool())
```

---

## 🔍 测试示例

### 示例1: 测试Shell命令执行

```python
class TestExecuteShellCommand(ToolTestBase):
    def get_tool_name(self) -> str:
        return "execute_shell_command"
    
    def run_tests(self):
        failures = []
        
        # 测试简单命令
        try:
            result = self.execute_tool({
                "command": "echo 'Hello, World!'"
            })
            self.assert_success(result)
            assert "Hello, World!" in result["stdout"]
        except AssertionError as e:
            failures.append(f"测试失败: {e}")
        
        return failures
```

### 示例2: 测试文件操作

```python
class TestReadFile(ToolTestBase):
    def get_tool_name(self) -> str:
        return "read_file"
    
    def run_tests(self):
        failures = []
        
        # 创建测试文件
        test_file = self.create_test_file(
            "test.txt", 
            "Test content"
        )
        
        try:
            result = self.execute_tool({"path": str(test_file)})
            self.assert_success(result)
            assert "Test content" in result["data"]
        finally:
            self.cleanup_test_file(test_file)
        
        return failures
```

---

## 🎓 最佳实践

### 1. 测试隔离
- 每个测试独立运行，不依赖其他测试
- 使用 `create_test_file()` 创建临时文件
- 使用 `cleanup_test_file()` 清理测试数据

### 2. 异常处理
- 使用 try-except 捕获断言错误
- 记录失败的测试到 failures 列表
- 确保清理代码在 finally 块中执行

### 3. 断言方法
- 使用基类提供的断言方法
- 提供清晰的错误消息
- 验证关键字段和数据结构

### 4. 测试数据
- 使用 `self.test_data_dir` 存储测试文件
- 测试后清理所有临时文件
- 避免使用硬编码路径

---

## 📈 测试报告

运行测试后会生成详细报告：

```
================================================================================
测试摘要
================================================================================
总测试数: 19
通过: 19 ✅
失败: 0 ❌
================================================================================

🎉 所有测试通过！
```

---

## 🔧 故障排查

### 问题1: 路径验证失败
**错误**: `ValueError: Path is not allowed`

**解决**: 确保测试路径在允许的目录中（如 `test_data_dir`）

### 问题2: 环境变量未加载
**错误**: `OPENAI_API_KEY is required`

**解决**: 确保 `.env` 文件存在且包含必要的API密钥

### 问题3: 工具未找到
**错误**: `Tool xxx not found`

**解决**: 检查工具名称是否正确，确保工具已在 `build_default_tools()` 中注册

---

## 🚀 未来扩展

### 待添加测试的工具 (31个)

1. **开发者工具**: git_log, run_python_script
2. **文档处理**: batch_summarize_documents, extract_text_from_documents
3. **媒体处理**: compress_images, capture_screenshot, get_video_info
4. **数据处理**: json_formatter, csv_analyzer, text_statistics
5. **高级文本**: grep_recursive, find_advanced, diff_files, port_killer
6. **其他**: open_app, open_url, spotlight_search, timezone_converter 等

### 扩展计划
1. 添加性能测试
2. 添加压力测试
3. 添加并发测试
4. 生成测试覆盖率报告

---

## 📚 相关文档

- [Mac Agent 工具说明](../../docs/mac_agent_工具说明_20260129.md)
- [智能体架构](../../../docs/refactoring/智能体架构.md)
- [工具实现](../../agent/tools/mac_tools.py)

---

## 👥 贡献指南

1. 遵循现有的测试结构和命名规范
2. 每个新工具都应该有对应的测试
3. 测试应该覆盖正常情况和异常情况
4. 提交前运行 `run_all_tests.py` 确保所有测试通过
