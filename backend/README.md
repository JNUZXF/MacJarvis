# MacOS Agent Backend v2.0

🚀 **生产级AI智能助手后端系统**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ 特性

### 🎯 核心功能

- **AI对话**: 基于GPT-4o-mini/Claude/Gemini的智能对话
- **工具执行**: 47个macOS系统工具的安全执行
- **记忆系统**: 短期、情节、语义三层记忆
- **文件处理**: PDF、Word、Excel、图片等多格式支持
- **流式响应**: Server-Sent Events实时输出

### 🏗️ 生产级特性

- ✅ **结构化日志**: JSON格式，支持ELK/Loki
- ✅ **分布式追踪**: OpenTelemetry集成
- ✅ **健康检查**: 完整的健康检查和监控
- ✅ **错误处理**: 自动重试和优雅降级
- ✅ **缓存系统**: Redis缓存降低API成本
- ✅ **异步任务**: Celery后台任务处理
- ✅ **数据库ORM**: SQLAlchemy 2.0异步支持
- ✅ **依赖注入**: 清晰的依赖管理
- ✅ **类型安全**: 完整的类型注解

---

## 🏛️ 架构

### 分层架构

```
backend/
├── app/
│   ├── api/              # 表现层 - API endpoints
│   ├── services/         # 应用层 - 业务逻辑
│   ├── core/             # 领域层 - 核心逻辑
│   ├── infrastructure/   # 基础设施层
│   ├── middleware/       # 中间件
│   └── utils/            # 工具函数
├── tests/                # 测试
├── migrations/           # 数据库迁移
├── docker/               # Docker配置
└── docs/                 # 文档
```

### 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| Web框架 | FastAPI | 0.115.0 |
| ASGI服务器 | Uvicorn | 0.32.0 |
| 数据库 | PostgreSQL/SQLite | 15/3 |
| ORM | SQLAlchemy | 2.0.36 |
| 缓存 | Redis | 7 |
| 任务队列 | Celery | 5.4.0 |
| 日志 | Structlog | 24.4.0 |
| 追踪 | OpenTelemetry | 1.28.2 |

---

## 🚀 快速开始

### 使用Docker（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
nano .env  # 填入OPENAI_API_KEY等配置

# 2. 启动服务
docker compose -f docker/docker-compose.yml up -d --build

# 3. 运行数据库迁移
docker compose exec api alembic upgrade head

# 4. 验证部署
curl http://localhost:8000/health/detailed
```

### 本地开发

```bash
# 1. 创建虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements-dev.txt

# 3. 配置环境变量
cp .env.example .env
# 使用SQLite: DATABASE_URL=sqlite+aiosqlite:///./backend_data/app.db

# 4. 初始化数据库
alembic upgrade head

# 5. 启动应用
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📚 API文档

### 访问文档

- **Swagger UI**: http://localhost:8000/docs (仅开发环境)
- **ReDoc**: http://localhost:8000/redoc (仅开发环境)

### 主要端点

#### 聊天

```bash
POST /api/v1/chat
Content-Type: application/json

{
  "message": "帮我列出当前目录的文件",
  "user_id": "user123",
  "session_id": "session456",
  "model": "gpt-4o-mini",
  "stream": true
}
```

#### 会话管理

```bash
# 初始化会话
POST /api/v1/session/init

# 创建新会话
POST /api/v1/session/new

# 获取会话
GET /api/v1/session/{session_id}?user_id=user123

# 列出会话
GET /api/v1/sessions?user_id=user123
```

#### 文件上传

```bash
POST /api/v1/files
Content-Type: multipart/form-data

file: <binary data>
```

#### 用户路径管理

```bash
# 获取用户路径
GET /api/v1/user/paths?user_id=user123

# 设置用户路径
POST /api/v1/user/paths
{
  "user_id": "user123",
  "paths": ["/Users/username/Documents"]
}
```

---

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 生成覆盖率报告
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### 测试覆盖率目标

- 单元测试: 70%+
- 集成测试: 主要API端点
- E2E测试: 关键业务流程

---

## 🔧 配置

### 环境变量

详见 `.env.example` 文件。

### 关键配置

```bash
# LLM配置
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o-mini
LLM_CACHE_ENABLED=true

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Redis配置
REDIS_URL=redis://localhost:6379/0

# 性能配置
DB_POOL_SIZE=20
REDIS_MAX_CONNECTIONS=50
```

---

## 📊 监控

### 健康检查

```bash
# 基础健康检查
curl http://localhost:8000/health

# 详细健康检查
curl http://localhost:8000/health/detailed | jq

# 指标
curl http://localhost:8000/metrics | jq
```

### 日志

日志文件位置：
- `logs/mac_agent.log` - 应用日志
- `logs/mac_agent_error.log` - 错误日志
- `logs/mac_agent_access.log` - 访问日志

查看实时日志：
```bash
tail -f logs/mac_agent.log | jq
```

---

## 🔒 安全

### 安全特性

- ✅ 环境变量存储敏感信息
- ✅ 日志自动脱敏
- ✅ 路径白名单验证
- ✅ SQL注入防护（ORM）
- ✅ 输入验证（Pydantic）
- ✅ 非root用户运行
- ✅ 安全响应头

### 安全建议

1. **生产环境必须**:
   - 使用HTTPS
   - 限制CORS origins
   - 使用强密码
   - 定期更新依赖
   - 启用防火墙

2. **定期审计**:
   - 检查日志中的异常访问
   - 审查用户路径配置
   - 更新安全补丁

---

## 📖 文档

- [架构设计文档](docs/architecture/20260128_architecture_design.md)
- [部署指南](docs/deployment/20260128_deployment_guide.md)
- [故障排查指南](docs/troubleshooting/20260128_troubleshooting_guide.md)
- [重构进度报告](docs/refactoring/20260128_refactoring_progress.md)

---

## 🛠️ 开发

### 代码规范

```bash
# 格式化代码
black app/ tests/
isort app/ tests/

# 类型检查
mypy app/

# 代码检查
pylint app/
```

### 提交前检查

```bash
# 运行所有检查
black --check app/
isort --check app/
mypy app/
pytest
```

---

## 📦 依赖管理

### 添加新依赖

```bash
# 1. 添加到requirements.txt
echo "new-package==1.0.0" >> requirements.txt

# 2. 重新构建镜像
docker compose build api

# 3. 重启服务
docker compose up -d api
```

### 更新依赖

```bash
# 查看过期包
pip list --outdated

# 更新特定包
pip install --upgrade package-name

# 更新requirements.txt
pip freeze > requirements.txt
```

---

## 🤝 贡献

欢迎贡献代码！请遵循以下流程：

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

---

## 📝 更新日志

### v2.0.0 (2026-01-28)

🎉 **重大重构 - 生产级标准**

**新增**:
- ✅ 完整的分层架构
- ✅ 结构化日志系统
- ✅ Redis缓存系统
- ✅ Celery异步任务
- ✅ SQLAlchemy ORM
- ✅ 依赖注入系统
- ✅ 完整的错误处理
- ✅ 监控和追踪支持

**改进**:
- ✅ 性能优化（缓存、连接池）
- ✅ 可观测性提升（日志、指标、追踪）
- ✅ 可维护性提升（分层、仓储模式）
- ✅ 可测试性提升（依赖注入、mock支持）

**破坏性变更**:
- API路径从 `/api/*` 改为 `/api/v1/*`
- 数据库从JSON文件改为SQLAlchemy ORM
- 配置从散落改为统一的Settings类

### v1.0.0 (2026-01-15)

- 初始版本
- 基础聊天功能
- 47个macOS工具
- 简单的记忆系统

---

## 📄 许可证

MIT License

---

## 🙏 致谢

感谢所有贡献者和开源社区！

---

**维护者**: MacAgent Team  
**项目主页**: https://github.com/your-org/mac-agent  
**问题反馈**: https://github.com/your-org/mac-agent/issues
