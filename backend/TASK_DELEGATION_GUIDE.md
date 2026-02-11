# 任务委托功能使用指南

## 快速开始

任务委托机制允许 mac_agent 将复杂或耗时的任务分配给独立的后台智能体执行，实现非阻塞对话。

### 核心功能

1. **DelegateTaskTool** - 委托任务给后台智能体
2. **CheckDelegatedTasksTool** - 查询后台任务状态和结果
3. **BackgroundAgentTask** - 在独立进程中执行任务
4. **自动通知** - 任务完成后主动通知用户

## 使用示例

### 场景：批量文件分析

```
用户: 帮我分析 ~/projects/myapp 下所有 Python 文件的代码复杂度

助手: 这个任务可能需要一些时间，让我委托给后台智能体处理。

[调用 delegate_task]

助手: 任务已委托给后台智能体（ID: a1b2c3d4），你可以继续问我其他问题。

用户: 现在几点？

助手: 下午 3:15

      对了，刚才的代码分析任务完成了！

      分析结果：
      - 共分析 45 个 Python 文件
      - 总代码行数: 12,350 行
      - 平均圈复杂度: 4.2
      - 需要优化的文件: 3 个

      [详细结果...]
```

## 工具 API

### delegate_task

**参数**:
- `task_description` (必填): 任务的详细描述
- `context` (可选): 任务上下文
  - `chat_history`: 相关聊天历史
  - `files`: 相关文件路径列表
  - `additional_info`: 其他自定义信息

**返回**:
```json
{
  "ok": true,
  "data": {
    "task_id": "uuid",
    "status": "pending",
    "message": "任务已委托..."
  }
}
```

### check_delegated_tasks

**参数**:
- `status_filter` (可选): 过滤状态 (`all`, `pending`, `running`, `completed`, `failed`)
- `limit` (可选): 返回数量限制，默认 10

**返回**:
```json
{
  "ok": true,
  "data": {
    "tasks": [...],
    "total_count": 5,
    "new_completed_count": 2,
    "message": "发现 2 个新完成的任务!"
  }
}
```

## 部署配置

### 1. 安装 Redis

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu
sudo apt-get install redis-server
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:alpine
```

### 2. 启动 Celery Worker

```bash
cd backend

# 开发环境
celery -A app.infrastructure.tasks.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --queues=ai,default

# 生产环境（后台运行）
celery -A app.infrastructure.tasks.celery_app worker \
    --loglevel=warning \
    --concurrency=4 \
    --queues=ai,default \
    --detach \
    --logfile=/var/log/celery/worker.log
```

### 3. 监控（可选）

```bash
# 安装 Flower
pip install flower

# 启动监控界面
celery -A app.infrastructure.tasks.celery_app flower

# 访问 http://localhost:5555
```

## 架构设计

### 数据流

```
用户请求 → mac_agent → DelegateTaskTool
                ↓
        创建数据库记录（pending）
                ↓
        启动 Celery 任务
                ↓
        返回任务 ID
                ↓
Celery Worker: 执行后台任务
                ↓
        更新状态（running）
                ↓
        创建独立 Agent 实例
                ↓
        执行任务并保存结果
                ↓
        更新状态（completed）
                ↓
mac_agent 定期检查 → CheckDelegatedTasksTool
                ↓
        发现完成任务
                ↓
        通知用户
```

### 数据库模型

**delegated_tasks 表**:
- `id`: 任务 ID (UUID)
- `user_id`: 用户 ID
- `session_id`: 会话 ID
- `task_description`: 任务描述
- `context`: 任务上下文 (JSON)
- `status`: 状态 (pending/running/completed/failed)
- `result`: 任务结果
- `error`: 错误信息
- `created_at`, `started_at`, `completed_at`: 时间戳
- `notified`: 是否已通知 (0/1)

## 适用场景

### ✅ 适合委托的任务

- 批量文件处理和分析
- 复杂的代码质量检查
- 长时间运行的测试套件
- 大规模文档生成
- 性能分析和优化建议
- 技术调研和资料整理

### ❌ 不适合委托的任务

- 简单的文件读取
- 需要用户交互确认的操作
- 实时性要求高的任务
- 非常短时间就能完成的操作

## 最佳实践

### 1. 清晰的任务描述

```python
# ✅ 好的任务描述
delegate_task(
    task_description="""
    分析项目代码质量：
    1. 统计代码行数和复杂度
    2. 检测重复代码
    3. 识别潜在bug
    4. 生成 Markdown 报告
    保存到 ~/.mac_agent/records/report/
    """
)

# ❌ 不好的任务描述
delegate_task(
    task_description="帮我看看代码"
)
```

### 2. 传递必要的上下文

```python
delegate_task(
    task_description="...",
    context={
        "files": ["/path/to/project"],
        "chat_history": recent_relevant_messages[-5:],  # 只传最近相关的
        "additional_info": {
            "output_format": "markdown",
            "language": "python"
        }
    }
)
```

### 3. 合理的任务粒度

```python
# ❌ 任务太大
delegate_task(description="分析整个代码库10000+文件")

# ✅ 合理拆分
for module in ["auth", "api", "database"]:
    delegate_task(description=f"分析 {module} 模块")
```

## 故障排查

### 问题1: 任务一直 pending

**原因**: Celery worker 未启动

**解决**:
```bash
# 检查 worker
ps aux | grep celery

# 启动 worker
celery -A app.infrastructure.tasks.celery_app worker --loglevel=info
```

### 问题2: 任务执行失败

**查看错误**:
```python
# 查询失败任务
check_delegated_tasks(status_filter="failed")

# 查看详细错误信息
```

**常见错误**:
- `TimeoutError`: 任务超时（超过30分钟）→ 拆分任务
- `FileNotFoundError`: 文件路径不存在 → 检查路径
- `OpenAI API Error`: API 调用失败 → 检查 API 密钥

### 问题3: Redis 连接失败

```bash
# 检查 Redis
redis-cli ping  # 应返回 PONG

# 启动 Redis
redis-server
```

## 性能优化

### Worker 并发配置

```bash
# 根据 CPU 核心数调整
CORES=$(nproc)

# CPU 密集型任务
celery worker --concurrency=$CORES

# IO 密集型任务
celery worker --concurrency=$((CORES * 2))
```

### 定期清理旧任务

系统会自动清理 30 天前的已完成/失败任务，保持数据库性能。

## 技术细节

### 依赖注入

```python
# ChatService 中自动注入
def _build_tool_registry(self):
    tools = build_default_tools()
    session_maker = get_session_maker(self.settings)

    for tool in tools:
        if tool.name in ("delegate_task", "check_delegated_tasks"):
            tool.db_session_factory = session_maker
        if tool.name == "delegate_task":
            tool.celery_app = celery_app
```

### 超时控制

- **硬超时**: 30 分钟（task_time_limit=1800）
- **软超时**: 25 分钟（task_soft_time_limit=1500）
- **重试**: 最多 2 次，指数退避（120s, 240s）

### 任务状态机

```
pending → running → completed
    ↓         ↓
    └─────→ failed (可重试)
```

## 相关文件

### 核心实现
- `backend/agent/tools/delegation/delegate_tool.py` - 委托工具
- `backend/agent/tools/delegation/check_tasks_tool.py` - 查询工具
- `backend/app/infrastructure/tasks/background_agent.py` - 后台执行器
- `backend/app/infrastructure/database/models.py` - DelegatedTask 模型

### 配置
- `backend/app/infrastructure/tasks/celery_app.py` - Celery 配置
- `backend/app/services/chat_service.py` - 依赖注入

### 注册
- `backend/agent/tools/mac_tools.py` - 工具注册（从 51 个增加到 53 个）

## 更新日志

### v1.0.0 (2024-01-15)
- ✨ 初始版本发布
- ✅ 基础任务委托功能
- ✅ 状态查询和通知
- ✅ Celery 集成
- ✅ 数据库持久化
- ✅ 错误处理和重试
- ✅ 超时保护

## 完整文档

更详细的文档请参考 `docs/features/task-delegation.md`（包含架构图、详细 API、最佳实践等）。

## 许可证

MIT License

---

**版本**: v1.0.0
**维护**: MacJarvis Team
