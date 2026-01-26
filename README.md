# MacJarvis - macOS 智能助手

<div align="center">

![MacJarvis](https://img.shields.io/badge/MacJarvis-AI%20Assistant-blue)
![Python](https://img.shields.io/badge/Python-3.12+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)
![React](https://img.shields.io/badge/React-19.2+-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

**一个基于 AI 的 macOS 智能助手系统，通过自然语言交互帮助用户管理系统、执行任务、排查问题**

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [架构设计](#-架构设计) • [API 文档](#-api-文档) • [开发指南](#-开发指南)

</div>

---

## 📋 目录

- [项目简介](#-项目简介)
- [功能特性](#-功能特性)
- [技术栈](#-技术栈)
- [项目结构](#-项目结构)
- [快速开始](#-快速开始)
- [配置说明](#-配置说明)
- [架构设计](#-架构设计)
- [API 文档](#-api-文档)
- [开发指南](#-开发指南)
- [部署指南](#-部署指南)
- [故障排查](#-故障排查)
- [安全注意事项](#-安全注意事项)
- [贡献指南](#-贡献指南)
- [更新日志](#-更新日志)

---

## 🎯 项目简介

MacJarvis 是一个智能化的 macOS 系统管理助手，通过自然语言对话的方式，帮助用户：

- 🔍 **系统监控**：实时查看系统状态、进程信息、资源使用情况
- 📁 **文件管理**：智能搜索、读取、创建、管理文件和目录
- 🌐 **网络诊断**：检查网络配置、端口状态、DNS 设置
- 🚀 **应用管理**：快速启动应用、管理已安装程序
- 🤖 **智能对话**：支持多模型切换，提供流畅的对话体验

系统采用前后端分离架构，支持流式响应和实时工具调用显示，提供现代化的 Web 界面和完整的 Docker 容器化部署方案。

---

## ✨ 功能特性

### 🤖 多模型支持

系统支持多种主流 AI 模型，可根据需求灵活切换：

- **OpenAI GPT-4o-mini**: 快速响应，适合日常任务，成本效益高
- **Anthropic Claude Haiku 4.5**: 高效推理，成本优化，适合复杂任务
- **Google Gemini 2.5 Flash**: 多模态能力，快速处理，适合大规模任务

所有模型通过 OpenRouter API 统一接入，支持一键切换。

### 🛠️ 丰富的系统工具

#### 系统信息
- **系统版本信息**：macOS 版本、内核版本、硬件信息
- **CPU 和内存监控**：实时查看 CPU 使用率、内存占用情况
- **进程管理**：按 CPU/内存排序查看进程，支持限制显示数量
- **磁盘空间**：查看磁盘使用情况，定位大文件
- **电池状态**：查看电池健康度和电源设置

#### 文件管理
- **目录浏览**：列出目录内容，支持递归查看
- **文件搜索**：按通配符模式搜索文件，支持限制结果数量
- **文件读取**：读取文件内容，支持大小限制（防止内存溢出）
- **文件写入**：创建或覆盖文件，支持内容验证
- **文件追加**：追加内容到文件，支持自动创建
- **目录创建**：创建目录结构，支持递归创建
- **文件信息**：获取文件/目录的详细信息（大小、权限、修改时间等）
- **文本搜索**：在文件中搜索文本内容（grep 功能）
- **文件删除**：安全删除文件到回收站

#### 网络工具
- **网络接口**：查看所有网络接口配置
- **DNS 配置**：查看系统 DNS 设置
- **Wi-Fi 信息**：查看当前 Wi-Fi 连接状态
- **端口监听**：查看系统监听的端口列表

#### 应用管理
- **应用列表**：列出所有已安装的应用程序
- **应用启动**：打开指定的应用程序
- **浏览器打开**：在默认浏览器中打开 URL

### 🔒 安全特性

- **路径访问限制**：仅允许访问用户目录（`~/`, `~/Desktop`, `~/Documents`, `~/Downloads`）
- **文件大小限制**：读取文件限制最大 50KB，写入文件限制最大 100KB
- **命令执行超时**：所有命令执行都有超时保护（默认 30 秒）
- **输入验证**：严格的参数验证和错误处理
- **错误隔离**：工具执行错误不会影响整个系统

### 💬 用户体验

- **流式响应**：实时显示 AI 回复内容，无需等待
- **工具调用可视化**：实时显示工具调用过程和结果
- **Markdown 支持**：AI 回复支持 Markdown 格式渲染
- **多会话管理**：支持创建多个会话并快速切换
- **用户标识**：每次进入自动生成唯一用户 ID，用于区分会话
- **响应式设计**：支持桌面和移动端访问
- **错误提示**：友好的错误提示和异常处理

---

## 🛠️ 技术栈

### 后端
- **Python 3.12+**: 现代 Python 特性支持
- **FastAPI**: 高性能异步 Web 框架
- **Uvicorn**: ASGI 服务器
- **httpx**: 异步 HTTP 客户端
- **Pydantic**: 数据验证和序列化

### 前端
- **React 19.2**: 最新版本的 React 框架
- **TypeScript**: 类型安全的 JavaScript
- **Vite**: 快速的前端构建工具
- **Tailwind CSS**: 实用优先的 CSS 框架
- **React Markdown**: Markdown 渲染组件
- **Server-Sent Events (SSE)**: 流式数据传输

### 部署
- **Docker**: 容器化部署
- **Docker Compose**: 多容器编排
- **Nginx**: 反向代理和静态文件服务

---

## 📁 项目结构

```
mac_agent/
├── src/                          # 后端源代码
│   ├── agent/                    # 智能体核心模块
│   │   ├── core/                # 核心组件
│   │   │   ├── agent.py         # Agent 主类（流式处理、工具调用）
│   │   │   ├── client.py        # OpenAI API 客户端封装
│   │   │   └── config.py        # 配置管理和模型验证
│   │   ├── tools/               # 工具模块
│   │   │   ├── base.py          # 工具基类定义
│   │   │   ├── registry.py      # 工具注册表和管理
│   │   │   ├── mac_tools.py     # macOS 系统工具集（20+ 工具）
│   │   │   ├── command_runner.py # 命令执行器（超时控制）
│   │   │   └── validators.py    # 路径验证和安全检查
│   │   └── app.py               # CLI 入口（命令行工具）
│   └── server/                  # FastAPI 服务器
│       └── app.py              # API 服务器（SSE 流式响应）
├── frontend/                    # 前端应用
│   ├── src/
│   │   ├── App.tsx             # 主应用组件
│   │   ├── components/         # UI 组件
│   │   │   ├── ChatMessage.tsx # 聊天消息组件
│   │   │   └── ToolCallDisplay.tsx # 工具调用显示组件
│   │   └── types.ts            # TypeScript 类型定义
│   ├── package.json            # 前端依赖配置
│   └── vite.config.ts          # Vite 构建配置
├── docker-compose.yml          # Docker Compose 配置
├── Dockerfile.backend          # 后端镜像构建文件
├── Dockerfile.frontend         # 前端镜像构建文件
├── nginx.conf                  # Nginx 配置文件
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量示例
└── README.md                   # 项目文档
```

---

## 🚀 快速开始

### 环境要求

- **Python**: 3.12 或更高版本
- **Node.js**: 18 或更高版本
- **Docker & Docker Compose**: 可选，用于容器化部署
- **macOS**: 系统工具仅支持 macOS（其他系统可修改工具实现）

### 方式一：本地开发

#### 1. 克隆项目

```bash
git clone git@github.com:JNUZXF/MacJarvis.git
cd MacJarvis
```

#### 2. 后端设置

```bash
# 进入后端目录
cd src

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r ../requirements.txt

# 配置环境变量
cd ..
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

#### 3. 前端设置

```bash
cd frontend
npm install
```

#### 4. 启动服务

**启动后端服务**（在项目根目录下）：

```bash
cd src
source .venv/bin/activate
cd server
python app.py
# 或使用 uvicorn（推荐，支持热重载）
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

后端服务将在 `http://localhost:8000` 启动。

**启动前端服务**（在 `frontend` 目录下）：

```bash
cd frontend
npm run dev
```

前端服务将在 `http://localhost:5173` 启动。

访问 `http://localhost:5173` 即可使用应用。

如需在本地直连后端（不经过 nginx 代理），请在启动前设置：
```bash
export VITE_API_URL=http://localhost:8000
```

### 方式二：Docker 部署（推荐）

#### 使用 Docker Compose

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key

# 2. 启动所有服务
docker compose -f docker-compose.yml up -d --build

# 3. 查看日志
docker compose -f docker-compose.yml logs -f

# 4. 停止服务
docker compose -f docker-compose.yml down
```

服务启动后：
- 前端访问：`http://localhost:8080`
- 后端 API：`http://localhost:8001`
- API 文档：`http://localhost:8001/docs`

#### 手动构建和运行

```bash
# 构建后端镜像
docker build -t macjarvis-backend -f Dockerfile.backend .

# 构建前端镜像
docker build -t macjarvis-frontend -f Dockerfile.frontend .

# 运行后端
docker run -d --name backend \
  -p 8001:8000 \
  --env-file .env \
  macjarvis-backend

# 运行前端
docker run -d --name frontend \
  -p 8080:80 \
  --link backend:backend \
  macjarvis-frontend
```

---

## ⚙️ 配置说明

### 环境变量

创建 `.env` 文件并配置以下变量：

```bash
# API 配置（推荐使用 OpenRouter）
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-4o-mini

# 可选配置
OPENAI_TIMEOUT_S=60          # API 请求超时时间（秒）
OPENAI_MAX_TOOL_TURNS=8      # 最大工具调用轮数
```

### 支持的模型

系统支持以下模型（需要在 OpenRouter 或其他兼容 API 中使用）：

- `openai/gpt-4o-mini` - OpenAI GPT-4o Mini（默认）
- `anthropic/claude-haiku-4.5` - Anthropic Claude Haiku 4.5
- `google/gemini-2.5-flash` - Google Gemini 2.5 Flash

### 路径安全限制

默认允许访问的目录：
- `~/` (用户主目录)
- `~/Desktop`
- `~/Documents`
- `~/Downloads`

如需修改允许的路径，推荐通过环境变量注入额外白名单，避免修改代码：

- `AGENT_ALLOWED_ROOTS`：使用系统路径分隔符（macOS/Linux 为 `:`）分隔多个路径
- 示例：`AGENT_ALLOWED_ROOTS=/Users/your_username:/Users/your_username/Desktop`

若必须修改默认白名单，可编辑 `src/agent/tools/validators.py` 中的 `BASE_ALLOWED_ROOTS` 列表：

```python
BASE_ALLOWED_ROOTS = [
    Path.home(),
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
    # 添加更多允许的路径
]
```

路径规范化支持常见变量展开，例如 `~`、`$HOME`/`$USER`、以及 `$(whoami)`，避免因变量未展开导致路径被拒绝。

#### 用户级路径白名单（前端配置）

- 前端支持用户配置个人路径白名单，后端会持久化到 `backend_data/user_paths.json`
- 路径校验会合并“默认白名单 + 环境变量白名单 + 用户白名单”
- 用户白名单只接受已存在的目录路径，且会拒绝根目录 `/`

API：
- `GET /api/user/paths?user_id=...` 获取用户白名单
- `POST /api/user/paths` 保存用户白名单（`{"user_id": "...", "paths": ["..."]}`）

**Docker 部署注意事项**：
- Docker 容器内已挂载用户主目录（`${HOME}:/host_home`），容器内 `HOME=/host_home`
- 智能体创建的 `~/Documents`、`~/Desktop` 等路径会映射到宿主机的用户目录
- 如果文件找不到，检查容器内路径：`docker exec macjarvis-backend ls -la /host_home/Documents`
- 确保容器有权限访问挂载的目录

---

## 🏗️ 架构设计

### 整体架构

```
┌─────────────┐
│  前端 (React) │
│  Port: 5173 │
└──────┬──────┘
       │ HTTP/SSE
       ▼
┌─────────────┐
│  Nginx      │
│  Port: 80   │
└──────┬──────┘
       │ Proxy
       ▼
┌─────────────┐      ┌──────────────┐
│ FastAPI     │─────▶│ OpenAI API  │
│ Backend     │      │ (OpenRouter) │
│ Port: 8000  │      └──────────────┘
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Agent Core │
│  + Tools    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ macOS System│
│ Commands    │
└─────────────┘
```

### 核心组件

#### 1. Agent 核心 (`agent/core/agent.py`)

- **流式处理**：支持 Server-Sent Events (SSE) 流式响应
- **工具调用循环**：自动处理多轮工具调用，直到获得最终结果
- **事件系统**：统一的事件类型（content、tool_start、tool_result）

#### 2. 工具系统 (`agent/tools/`)

- **工具注册表**：统一管理所有可用工具
- **工具执行器**：安全的命令执行，带超时控制
- **路径验证器**：确保文件操作的安全性

#### 3. API 服务器 (`server/app.py`)

- **FastAPI 路由**：RESTful API 设计
- **SSE 流式响应**：实时推送 AI 回复和工具调用结果
- **错误处理**：统一的异常处理和错误格式

#### 4. 前端应用 (`frontend/src/`)

- **React Hooks**：使用现代 React Hooks 管理状态
- **SSE 客户端**：使用 `@microsoft/fetch-event-source` 处理流式数据
- **Markdown 渲染**：使用 `react-markdown` 渲染 AI 回复

### 数据流

1. **用户输入** → 前端发送 POST 请求到 `/api/chat`
2. **后端处理** → Agent 接收消息，调用 OpenAI API
3. **流式响应** → 通过 SSE 实时推送内容块和工具调用事件
4. **工具执行** → Agent 调用工具，执行系统命令
5. **结果返回** → 工具结果通过 SSE 返回，Agent 继续处理
6. **前端渲染** → 实时更新 UI，显示 AI 回复和工具调用状态

---

## 📡 API 文档

### POST /api/chat

发送聊天消息并获取流式响应。

**请求体**:
```json
{
  "message": "查看系统信息",
  "model": "openai/gpt-4o-mini"  // 可选，不指定则使用默认模型
}
```

**响应格式** (Server-Sent Events):

```
event: content
data: "系统信息如下..."

event: tool_start
data: {"tool_call_id": "xxx", "name": "system_info", "args": {}}

event: tool_result
data: {"tool_call_id": "xxx", "result": {"ok": true, "data": {...}}}

event: error
data: "错误信息"
```

**事件类型**:

- `content`: AI 回复的文本内容（流式）
- `tool_start`: 工具开始调用
- `tool_result`: 工具执行结果
- `error`: 错误信息

### GET /health

健康检查端点，返回服务状态。

**响应**:
```json
{
  "status": "ok",
  "service": "macjarvis-backend"
}
```

### GET /docs

FastAPI 自动生成的 API 文档（Swagger UI）。

---

## 🛠️ 开发指南

### 添加新工具

1. 在 `src/agent/tools/mac_tools.py` 中创建工具类：

```python
@dataclass
class MyNewTool:
    name: str = "my_new_tool"
    description: str = "工具描述"
    parameters: dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "参数1的描述"
                    }
                },
                "required": ["param1"]
            }
    
    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        # 实现工具逻辑
        param1 = args.get("param1")
        # ... 执行操作 ...
        return {"ok": True, "data": "结果"}
```

2. 在 `build_default_tools()` 函数中注册工具：

```python
def build_default_tools() -> list[Any]:
    return [
        # ... 其他工具
        MyNewTool(),
    ]
```

3. 工具返回值格式：

```python
# 成功
{"ok": True, "data": {...}}

# 失败
{"ok": False, "error": "错误描述"}
```

### 添加新模型

在 `src/agent/core/config.py` 中的 `ALLOWED_MODELS` 列表添加新模型：

```python
ALLOWED_MODELS = [
    # ... 现有模型
    "new-provider/new-model",
]
```

### 修改系统提示词

编辑 `src/server/app.py` 中的 `SYSTEM_PROMPT` 变量：

```python
SYSTEM_PROMPT = """你是一个专业的 macOS 智能助手...
你的自定义提示词...
"""
```

### 前端开发

```bash
cd frontend
npm run dev      # 开发模式（热重载）
npm run build    # 生产构建
npm run lint     # 代码检查
```

### 代码规范

- **Python**: 遵循 PEP 8 规范，使用类型提示
- **TypeScript**: 使用严格的类型检查，遵循 ESLint 规则
- **提交信息**: 使用清晰的提交信息，遵循 Conventional Commits

---

## 🐳 部署指南

### Docker Compose 部署（推荐）

1. **准备环境变量文件**：

```bash
cp .env.example .env
# 编辑 .env 文件
```

2. **启动服务**：

```bash
docker compose -f docker-compose.yml up -d --build
```

3. **查看日志**：

```bash
# 查看所有服务日志
docker compose -f docker-compose.yml logs -f

# 查看特定服务日志
docker compose -f docker-compose.yml logs -f backend
docker compose -f docker-compose.yml logs -f frontend
```

4. **停止服务**：

```bash
docker compose -f docker-compose.yml down
```

5. **更新服务**：

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker compose -f docker-compose.yml up -d --build
```

### 生产环境部署建议

1. **使用 HTTPS**：配置 SSL 证书，使用 Nginx 反向代理
2. **环境变量管理**：使用 Docker secrets 或环境变量管理服务
3. **日志管理**：配置日志轮转和集中日志收集
4. **监控告警**：配置健康检查和监控告警
5. **备份策略**：定期备份配置和数据

---

## 🔧 故障排查

### 后端无法启动

1. **检查 Python 版本**：
   ```bash
   python3 --version  # 需要 3.12+
   ```

2. **检查依赖安装**：
   ```bash
   pip list | grep fastapi
   ```

3. **检查环境变量**：
   ```bash
   # 确保 .env 文件存在且 OPENAI_API_KEY 已设置
   cat .env
   ```

4. **查看日志**：
   ```bash
   # 查看控制台输出的错误信息
   python app.py
   ```

### 前端无法连接后端

1. **确认后端服务运行**：
   ```bash
   # 本地开发
   curl http://localhost:8000/health
   # Docker 部署
   curl http://localhost:8001/health
   ```

2. **检查 CORS 配置**：后端已配置允许所有来源，如仍有问题检查网络请求

3. **检查浏览器控制台**：查看网络请求错误信息

4. **检查 API URL 配置**：
   ```bash
   # 前端使用相对路径，由 nginx 代理
   # 确保 nginx.conf 配置正确
   ```

### Docker 容器无法启动

1. **检查 Docker 服务状态**：
   ```bash
   docker ps
   docker compose -f docker-compose.yml ps
   ```

2. **查看容器日志**：
   ```bash
   docker compose -f docker-compose.yml logs
   ```

3. **检查环境变量文件**：
   ```bash
   # 确保 .env 文件存在且格式正确
   cat .env
   ```

4. **检查端口占用**：
   ```bash
   # macOS/Linux
   lsof -i :8000
   lsof -i :8001
   lsof -i :8080
   
   # 或使用 netstat
   netstat -an | grep 8000
   netstat -an | grep 8001
   ```

### API 请求失败

1. **检查 API Key**：
   ```bash
   # 确保 OPENAI_API_KEY 正确设置
   echo $OPENAI_API_KEY
   ```

2. **测试 API 连接**：
   ```bash
   # 本地开发
   curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "test"}'

   # Docker 部署
   curl -X POST http://localhost:8001/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "test"}'
   ```

3. **查看详细错误**：
   - 检查后端日志
   - 检查浏览器网络请求详情

---

## 🔒 安全注意事项

⚠️ **重要安全提示**：

1. **API Key 安全**：
   - 不要将 `.env` 文件提交到 Git 仓库
   - 使用环境变量或密钥管理服务存储敏感信息
   - 定期轮换 API Key

2. **路径限制**：
   - 系统已限制文件访问路径，请勿随意放宽限制
   - 生产环境中建议进一步限制工具权限

3. **命令执行**：
   - 工具会执行系统命令，请谨慎使用
   - 不要在生产环境中执行危险操作

4. **网络安全**：
   - 生产环境建议使用 HTTPS
   - 配置防火墙规则，限制访问来源

5. **输入验证**：
   - 所有用户输入都经过验证
   - 文件大小和路径都有严格限制

6. **日志安全**：
   - 避免在日志中记录敏感信息
   - 定期清理日志文件

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 贡献流程

1. **Fork 本项目**
2. **创建特性分支**：
   ```bash
   git checkout -b feature/AmazingFeature
   ```
3. **提交更改**：
   ```bash
   git commit -m 'Add some AmazingFeature'
   ```
4. **推送到分支**：
   ```bash
   git push origin feature/AmazingFeature
   ```
5. **开启 Pull Request**

### 代码规范

- 遵循项目的代码风格和规范
- 添加必要的注释和文档
- 确保代码通过测试
- 更新相关文档

### 报告问题

提交 Issue 时，请包含：
- 问题描述
- 复现步骤
- 预期行为
- 实际行为
- 环境信息（OS、Python 版本等）

---

## 📝 更新日志

### v1.0.0 (2026-01-26)

#### ✨ 新功能
- 初始版本发布
- 支持多模型切换（OpenAI、Anthropic、Google）
- 丰富的 macOS 系统管理工具（20+ 工具）
- 流式响应和实时工具调用显示
- Docker 容器化部署支持
- 路径访问安全限制
- 完整的文档和示例

#### 🛠️ 技术特性
- FastAPI 后端，支持 SSE 流式响应
- React 19 + TypeScript 前端
- 工具化架构，易于扩展
- 完善的错误处理和日志记录

#### 🔒 安全特性
- 路径访问限制
- 文件大小限制
- 命令执行超时控制
- 输入验证和错误处理

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 📮 联系方式

- **GitHub**: [JNUZXF/MacJarvis](https://github.com/JNUZXF/MacJarvis)
- **Issues**: [GitHub Issues](https://github.com/JNUZXF/MacJarvis/issues)
- **Pull Requests**: [GitHub Pull Requests](https://github.com/JNUZXF/MacJarvis/pulls)

---

## 🙏 致谢

感谢以下开源项目的支持：

- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的 Web 框架
- [React](https://react.dev/) - 用户界面库
- [OpenRouter](https://openrouter.ai/) - 统一的 AI API 接口
- [Tailwind CSS](https://tailwindcss.com/) - 实用优先的 CSS 框架

---

<div align="center">

**Made with ❤️ by JNUZXF**

⭐ 如果这个项目对你有帮助，请给个 Star！

</div>
