# Mac Agent 测试框架 - 快速开始

> 5分钟快速上手测试框架

---

## 🚀 快速运行

### 1. 运行所有测试

```bash
cd /Users/xinfuzhang/Desktop/Code/mac_agent/backend
source .venv/bin/activate
python tests/tools/run_all_tests.py
```

**预期输出**:
```
✅ 已加载环境变量
================================================================================
Mac Agent 工具全面测试
================================================================================
...
🎉 所有测试通过！
```

---

## 📝 添加新测试 (3步)

### 步骤1: 创建测试类

```python
# tests/tools/your_category/test_your_tool.py

from tests.tools.base import ToolTestBase

class TestYourTool(ToolTestBase):
    def get_tool_name(self) -> str:
        return "your_tool_name"  # 工具名称
    
    def run_tests(self):
        failures = []
        
        try:
            print("\n测试: 基本功能")
            result = self.execute_tool({"param": "value"})
            self.assert_success(result)
            print("✅ 通过")
        except AssertionError as e:
            failures.append(f"测试失败: {e}")
            print(f"❌ 失败: {e}")
        
        return failures
```

### 步骤2: 注册测试

```python
# tests/tools/run_all_tests.py

from tests.tools.your_category.test_your_tool import TestYourTool

runner.register_test(TestYourTool())
```

### 步骤3: 运行测试

```bash
python tests/tools/run_all_tests.py
```

---

## 🎯 常用断言

```python
# 成功/失败
self.assert_success(result)
self.assert_failure(result)

# 数据检查
self.assert_has_data(result)
self.assert_has_data(result, "field_name")

# 错误信息
self.assert_error_contains(result, "error text")
```

---

## 📁 测试数据管理

```python
# 创建测试文件
test_file = self.create_test_file("test.txt", "content")

try:
    # 使用文件
    result = self.execute_tool({"path": str(test_file)})
finally:
    # 清理文件
    self.cleanup_test_file(test_file)
```

---

## 📊 当前测试覆盖

| 分类 | 工具数 | 状态 |
|------|--------|------|
| 系统信息 | 4 | ✅ |
| 文件操作 | 5 | ✅ |
| Shell命令 | 3 | ✅ |
| 网络工具 | 3 | ✅ |
| 生产力 | 4 | ✅ |
| **总计** | **19** | **✅** |

---

## 🔗 更多信息

- [完整文档](./README.md)
- [测试框架说明](../../docs/测试框架说明_20260129.md)
- [工具说明](../../docs/mac_agent_工具说明_20260129.md)
