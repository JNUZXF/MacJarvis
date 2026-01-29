# 智能体记忆系统使用指南

## 概述

这是一个完善的智能体记忆系统，能够让智能体随着与用户交流的增多而越来越了解用户。系统支持5种记忆类型，并具备自动提取、存储、检索和定期优化功能。

## 记忆类型

| 记忆类型 | 描述 | 典型场景 | 数据表 |
|---------|------|---------|--------|
| **偏好记忆** | 用户表达的明确偏好 | "我喜欢简洁的回复"、"我是素食主义者" | `preference_memory` |
| **事实记忆** | 关于用户的客观信息 | 姓名、职业、家庭成员、地址 | `fact_memory` |
| **情景记忆** | 特定对话事件 | "上周讨论了巴黎旅行计划" | `episodic_memory` |
| **任务记忆** | 进行中的工作状态 | 项目进度、待办事项、文档版本 | `task_memory` |
| **关系记忆** | 实体间的关联 | "Alice是Bob的经理"、"项目X属于团队Y" | `relation_memory` |

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    对话流程 (Chat Flow)                      │
├─────────────────────────────────────────────────────────────┤
│  用户消息 → 记忆注入 → LLM 处理 → 记忆提取 → 助手回复        │
└─────────────────────────────────────────────────────────────┘
                         ↓           ↑
┌──────────────────────────────────────────────────────────────┐
│              记忆集成服务 (Memory Integration)                │
├──────────────────────────────────────────────────────────────┤
│  • 构建用户上下文提示                                          │
│  • 后台提取记忆                                               │
│  • 格式化记忆用于显示                                          │
└──────────────────────────────────────────────────────────────┘
        ↓                       ↑
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   记忆提取器      │  │   记忆管理器      │  │   记忆整合器      │
│ (LLM-based)      │  │   (CRUD)         │  │   (定期优化)      │
├──────────────────┤  ├──────────────────┤  ├──────────────────┤
│ • 分析对话内容    │  │ • 存储记忆        │  │ • 置信度衰减      │
│ • 提取结构化信息  │  │ • 检索记忆        │  │ • 清理低置信度    │
│ • 分类记忆类型    │  │ • 更新记忆        │  │ • 完成旧任务      │
└──────────────────┘  │ • 去重检测        │  │ • 合并重复记忆    │
                      └──────────────────┘  └──────────────────┘
                               ↓
                      ┌──────────────────┐
                      │    数据库层       │
                      ├──────────────────┤
                      │ • 5个记忆表       │
                      │ • 索引优化        │
                      │ • 外键约束        │
                      └──────────────────┘
```

## 核心组件

### 1. 数据库模型 (`backend/app/infrastructure/database/models.py`)

```python
class PreferenceMemory(Base):
    """偏好记忆表"""
    id, user_id, category, preference_key, preference_value
    confidence, source, metadata
    created_at, updated_at, last_confirmed_at

class FactMemory(Base):
    """事实记忆表"""
    id, user_id, fact_type, subject, fact_value
    confidence, source, metadata
    created_at, updated_at, verified_at

class TaskMemory(Base):
    """任务记忆表"""
    id, user_id, session_id, task_type, title, description
    status, progress, priority, context, metadata
    created_at, updated_at, due_date, completed_at

class RelationMemory(Base):
    """关系记忆表"""
    id, user_id, subject_entity, subject_type, relation_type
    object_entity, object_type, confidence, bidirectional
    metadata, created_at, updated_at
```

### 2. 记忆提取器 (`backend/app/services/memory_extractor.py`)

使用 LLM 从对话中提取结构化记忆：

```python
extractor = MemoryExtractor(llm_service)

# 从单次对话提取
memories = await extractor.extract_from_single_message(
    user_message="我是素食主义者，正在做一个Python项目",
    assistant_response="好的，我会记住您的饮食偏好。关于Python项目...",
    user_id="user123",
    session_id="session456"
)

# 结果示例:
# {
#   "preferences": [
#     {"category": "food", "key": "dietary_restriction",
#      "value": "vegetarian", "confidence": 10}
#   ],
#   "facts": [],
#   "tasks": [
#     {"type": "project", "title": "Python项目", "status": "active"}
#   ],
#   "relations": []
# }
```

### 3. 记忆管理器 (`backend/app/services/memory_manager.py`)

管理所有记忆的存储、检索和更新：

```python
manager = MemoryManager(db_session)

# 添加偏好（自动去重）
pref = await manager.add_preference(
    user_id="user123",
    category="communication",
    preference_key="response_style",
    preference_value="concise",
    confidence=8,
    source="explicit"
)

# 添加事实
fact = await manager.add_fact(
    user_id="user123",
    fact_type="personal",
    subject="name",
    fact_value="张三",
    confidence=10
)

# 添加任务
task = await manager.add_task(
    user_id="user123",
    task_type="project",
    title="完成用户认证功能",
    status="active",
    priority="high"
)

# 添加关系
relation = await manager.add_relation(
    user_id="user123",
    subject_entity="Alice",
    subject_type="person",
    relation_type="is_manager_of",
    object_entity="Bob",
    object_type="person",
    confidence=9
)

# 批量添加提取的记忆
counts = await manager.add_extracted_memories(
    extracted=memories,
    user_id="user123",
    session_id="session456"
)

# 获取用户完整上下文
context = await manager.get_user_context(
    user_id="user123",
    max_items_per_type=10
)
```

### 4. 记忆整合器 (`backend/app/services/memory_consolidator.py`)

定期优化和清理记忆：

```python
consolidator = MemoryConsolidator(db_session)

# 整合单个用户的记忆
stats = await consolidator.consolidate_user_memories("user123")
# 返回: {
#   "preferences_decayed": 5,
#   "preferences_removed": 2,
#   "facts_decayed": 3,
#   ...
# }

# 获取记忆统计
stats = await consolidator.get_memory_statistics("user123")
# 返回: {
#   "total_preferences": 15,
#   "total_facts": 30,
#   "active_tasks": 5,
#   "avg_preference_confidence": 7.5,
#   ...
# }
```

### 5. 记忆集成服务 (`backend/app/services/memory_integration_service.py`)

将记忆系统集成到对话流程：

```python
integration = MemoryIntegrationService(extractor, manager)

# 构建记忆上下文提示
prompt = await integration.build_memory_context_prompt("user123")
# 返回格式化的提示文本，包含用户的偏好、事实、任务等

# 后台提取记忆（不阻塞响应）
await integration.extract_and_store_memories(
    user_id="user123",
    session_id="session456",
    user_message="...",
    assistant_response="...",
    background=True
)

# 获取记忆摘要
summary = await integration.get_user_memory_summary("user123")
```

## 数据库迁移

运行迁移脚本创建记忆表：

```bash
cd backend

# 方式1: 使用 SQL 迁移文件
sqlite3 backend_data/app.db < migrations/add_memory_system_tables.sql

# 方式2: 使用 Alembic（如果配置了）
alembic upgrade head
```

## API 端点

所有端点都在 `/api/v1/memories/` 前缀下：

### 获取记忆上下文
```http
GET /api/v1/memories/{user_id}/context?max_items=10
```

响应：
```json
{
  "user_id": "user123",
  "preferences": [
    {"key": "response_style", "value": "concise", "confidence": 8}
  ],
  "facts": [
    {"subject": "name", "value": "张三", "type": "personal"}
  ],
  "active_tasks": [
    {"title": "完成用户认证", "status": "active", "priority": "high"}
  ],
  "relations": [
    {"subject": "Alice", "relation": "is_manager_of", "object": "Bob"}
  ]
}
```

### 获取偏好
```http
GET /api/v1/memories/{user_id}/preferences?category=food&limit=50
```

### 获取事实
```http
GET /api/v1/memories/{user_id}/facts?fact_type=personal&limit=100
```

### 获取任务
```http
GET /api/v1/memories/{user_id}/tasks?status=active&limit=50
```

### 获取关系
```http
GET /api/v1/memories/{user_id}/relations?entity=Alice&limit=100
```

### 获取统计信息
```http
GET /api/v1/memories/{user_id}/statistics
```

### 手动触发整合
```http
POST /api/v1/memories/{user_id}/consolidate
```

### 删除记忆
```http
DELETE /api/v1/memories/{user_id}/preferences/{preference_id}
DELETE /api/v1/memories/{user_id}/facts/{fact_id}
```

### 更新任务
```http
PATCH /api/v1/memories/{user_id}/tasks/{task_id}
Content-Type: application/json

{
  "status": "completed",
  "progress": 100
}
```

## 对话流程集成

记忆系统已自动集成到 `ChatService` 中：

1. **对话开始前** - 自动注入用户记忆上下文到系统提示
2. **对话完成后** - 后台提取记忆并存储

```python
# backend/app/services/chat_service.py

# 在构建系统提示时注入记忆
if self.memory:
    memory_context = await self.memory.build_memory_context_prompt(user_id)

messages = self._build_llm_messages(
    message=message,
    attachment_context=attachment_context,
    image_parts=image_parts,
    history=history,
    memory_context=memory_context  # 注入记忆上下文
)

# 对话完成后提取记忆（后台运行）
if self.memory:
    await self.memory.extract_and_store_memories(
        user_id=user_id,
        session_id=session_id,
        user_message=message,
        assistant_response=assistant_content,
        background=True  # 不阻塞响应
    )
```

## 依赖注入配置

在 `backend/app/dependencies.py` 中配置记忆服务：

```python
from app.services.memory_extractor import MemoryExtractor
from app.services.memory_manager import MemoryManager
from app.services.memory_integration_service import MemoryIntegrationService

async def get_memory_integration_service(
    db: AsyncSession = Depends(get_db_session),
    llm_service: LLMService = Depends(get_llm_service)
) -> MemoryIntegrationService:
    """Get memory integration service"""
    extractor = MemoryExtractor(llm_service)
    manager = MemoryManager(db)
    return MemoryIntegrationService(extractor, manager)

# 在 ChatService 中使用
async def get_chat_service(
    llm_service: LLMService = Depends(get_llm_service),
    session_service: SessionService = Depends(get_session_service),
    file_service: FileService = Depends(get_file_service),
    conversation_history: ConversationHistoryService = Depends(...),
    memory_service: MemoryIntegrationService = Depends(get_memory_integration_service),
    settings: Settings = Depends(get_settings)
) -> ChatService:
    return ChatService(
        llm_service=llm_service,
        session_service=session_service,
        file_service=file_service,
        conversation_history_service=conversation_history,
        settings=settings,
        memory_integration_service=memory_service  # 注入记忆服务
    )
```

## 定期整合任务

使用 Celery 或类似任务调度器定期运行记忆整合：

```python
# backend/app/infrastructure/tasks/workers.py

from celery import shared_task
from app.services.memory_consolidator import MemoryConsolidator

@shared_task
def consolidate_all_memories():
    """每天运行一次，整合所有用户的记忆"""
    async def run():
        async with get_db_session() as db:
            consolidator = MemoryConsolidator(db)
            stats = await consolidator.consolidate_all_users(limit=1000)
            logger.info(f"Memory consolidation completed: {stats}")

    asyncio.run(run())

# 在 Celery Beat 配置中：
# app.conf.beat_schedule = {
#     'consolidate-memories': {
#         'task': 'workers.consolidate_all_memories',
#         'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点
#     },
# }
```

## 配置选项

在 `backend/app/config.py` 中可配置的选项：

```python
class Settings(BaseSettings):
    # 记忆系统配置
    MEMORY_EXTRACTION_ENABLED: bool = True  # 是否启用记忆提取
    MEMORY_EXTRACTION_BACKGROUND: bool = True  # 是否后台提取
    MEMORY_CONTEXT_MAX_ITEMS: int = 10  # 上下文中每种类型的最大数量
    MEMORY_CONSOLIDATION_ENABLED: bool = True  # 是否启用定期整合

    # 置信度配置
    MEMORY_MIN_CONFIDENCE: int = 2  # 最低置信度阈值
    MEMORY_CONFIDENCE_DECAY_RATE: float = 0.1  # 每月衰减率
```

## 使用示例

### 示例 1: 智能体记住用户偏好

**对话 1:**
```
用户: 我喜欢简洁直接的回复，不要太啰嗦
助手: 好的，我会记住。简洁回复。
```

系统自动提取并存储：
```python
{
  "preferences": [
    {
      "category": "communication",
      "key": "response_style",
      "value": "concise and direct",
      "confidence": 9
    }
  ]
}
```

**对话 2 (几天后):**
```
用户: 帮我写个函数
助手: [系统提示中自动注入: 用户偏好简洁回复]
      好的。要实现什么功能？
```

### 示例 2: 追踪项目进度

**对话:**
```
用户: 我在做一个电商网站，需要实现用户认证、商品目录和购物车
助手: 好的，我帮你规划一下...
```

系统自动创建任务记忆：
```python
{
  "tasks": [
    {
      "title": "实现用户认证",
      "type": "project",
      "status": "active",
      "priority": "high"
    },
    {
      "title": "实现商品目录",
      "type": "project",
      "status": "active",
      "priority": "medium"
    },
    {
      "title": "实现购物车",
      "type": "project",
      "status": "active",
      "priority": "medium"
    }
  ]
}
```

后续对话中，智能体会自动注入这些任务信息，能够：
- 询问项目进度
- 提供针对性建议
- 继续之前的工作

### 示例 3: 记住关系网络

**对话:**
```
用户: Alice是我的项目经理，Bob是团队技术负责人
助手: 明白了。我会记住团队结构。
```

系统存储关系记忆：
```python
{
  "relations": [
    {
      "subject": "Alice",
      "relation": "is_manager_of",
      "object": "user",
      "confidence": 10
    },
    {
      "subject": "Bob",
      "relation": "is_tech_lead_of",
      "object": "team",
      "confidence": 10
    }
  ]
}
```

## 最佳实践

1. **置信度管理**
   - 直接陈述: confidence = 9-10
   - 推断信息: confidence = 5-7
   - 不确定: confidence = 2-4

2. **记忆更新策略**
   - 新信息置信度 >= 现有记忆 → 更新
   - 新信息置信度 < 现有记忆 → 保留原记忆

3. **隐私保护**
   - 敏感信息加密存储
   - 提供用户删除记忆的接口
   - 定期清理低置信度记忆

4. **性能优化**
   - 后台提取记忆，不阻塞对话
   - 使用数据库索引加速查询
   - 缓存热门记忆上下文

## 故障排查

### 记忆提取失败
```python
# 检查日志
logger.error("memory_extraction_failed", user_id=user_id, error=str(e))

# 可能原因:
# 1. LLM API 调用失败 → 检查 API 密钥和配额
# 2. JSON 解析失败 → 检查 LLM 响应格式
# 3. 数据库写入失败 → 检查数据库连接和权限
```

### 记忆不显示
```python
# 检查记忆是否存在
stats = await consolidator.get_memory_statistics(user_id)
print(stats)  # 查看记忆数量

# 检查置信度
# 低置信度记忆可能被清理了
```

### 重复记忆
```python
# 手动触发去重
await consolidator.consolidate_user_memories(user_id)
```

## 扩展功能

### 1. 语义搜索（未来增强）
使用向量嵌入进行语义记忆检索：
```python
# 为记忆生成嵌入
embedding = await embedder.embed(memory_content)

# 相似度搜索
similar_memories = await manager.search_by_embedding(
    user_id=user_id,
    query_embedding=embedding,
    limit=5
)
```

### 2. 记忆图谱可视化
提供 API 返回记忆关系图：
```python
GET /api/v1/memories/{user_id}/graph
```

### 3. 记忆导出
允许用户导出所有记忆数据：
```python
GET /api/v1/memories/{user_id}/export?format=json
```

## 总结

这个记忆系统提供了：
- ✅ 5种记忆类型全面覆盖
- ✅ 自动记忆提取和存储
- ✅ 智能去重和更新
- ✅ 定期优化和清理
- ✅ 完整的 REST API
- ✅ 无缝集成到对话流程
- ✅ 可扩展的架构设计

智能体将随着使用次数的增加，越来越了解用户，提供更加个性化和贴心的服务！
