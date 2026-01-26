# MacJarvis - macOS 智能助手

MacJarvis 是一个基于 AI 的 macOS 智能助手系统，通过自然语言交互帮助用户管理系统、执行任务、排查问题。系统支持多种 AI 模型（OpenAI、Anthropic、Google），并提供丰富的系统管理工具。

## 功能特性

### 🤖 多模型支持
- **OpenAI GPT-4o-mini**: 快速响应，适合日常任务
- **Anthropic Claude Haiku 4.5**: 高效推理，成本优化
- **Google Gemini 2.5 Flash**: 多模态能力，快速处理

### 🛠️ 丰富的系统工具

#### 系统信息
- 系统版本、内核、硬件信息
- CPU、内存使用情况
- 进程监控（按 CPU/内存排序）
- 磁盘空间使用情况
- 电池状态和电源设置

#### 文件管理
- 列出目录内容
- 搜索文件（支持通配符）
- 读取文件内容
- 写入/追加文件
- 创建目录
- 获取文件信息
- 文件内文本搜索
- 移动到回收站

#### 网络工具
- 网络接口信息
- DNS 配置
- Wi-Fi 连接信息
- 监听端口列表

#### 应用管理
- 列出已安装应用
- 打开指定应用
- 在浏览器中打开 URL

### 🔒 安全特性
- 路径访问限制（仅允许用户目录）
- 文件大小限制（防止内存溢出）
- 命令执行超时控制
- 输入验证和错误处理

## 项目结构

```
knowledgebase/
├── src/
│   ├── agent/              # 智能体核心模块
│   │   ├── core/          # 核心组件
│   │   │   ├── agent.py   # Agent 主类
│   │   │   ├── client.py  # API 客户端
│   │   │   └── config.py  # 配置管理
│   │   └── tools/         # 工具模块
│   │       ├── base.py    # 工具基类
│   │       ├── registry.py # 工具注册表
│   │       ├── mac_tools.py # macOS 工具集
│   │       └── validators.py # 路径验证
│   └── server/            # FastAPI 后端服务
│       └── app.py         # API 服务器
├── frontend/              # React + TypeScript 前端
│   ├── src/
│   │   ├── App.tsx        # 主应用组件
│   │   ├── components/    # UI 组件
│   │   └── types.ts       # TypeScript 类型定义
│   └── package.json       # 前端依赖
├── docker-compose.yml     # Docker Compose 配置
├── Dockerfile             # Docker 镜像构建文件
├── requirements.txt       # Python 依赖
└── README.md             # 项目文档
```

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose (可选，用于容器化部署)

### 本地开发

#### 1. 克隆项目

```bash
git clone git@github.com:JNUZXF/MacJarvis.git
cd MacJarvis
```

#### 2. 后端设置

```bash
# 创建虚拟环境
cd src
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r ../requirements.txt

# 配置环境变量
cp ../.env.example ../.env
# 编辑 .env 文件，填入你的 API Key
```

#### 3. 前端设置

```bash
cd frontend
npm install
```

#### 4. 启动服务

**后端服务**（在 `src` 目录下）:
```bash
source .venv/bin/activate
cd server
python app.py
# 或使用 uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

**前端服务**（在 `frontend` 目录下）:
```bash
npm run dev
```

访问 `http://localhost:5173` 使用应用。

### Docker 部署

#### 使用 Docker Compose（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 2. 启动所有服务
docker compose -f docker-compose.yml up -d

# 3. 查看日志
docker compose -f docker-compose.yml logs -f

# 4. 停止服务
docker compose -f docker-compose.yml down
```

#### 手动构建

```bash
# 构建后端镜像
docker build -t macjarvis-backend -f Dockerfile.backend .

# 构建前端镜像
docker build -t macjarvis-frontend -f Dockerfile.frontend .

# 运行后端
docker run -d --name backend \
  -p 8000:8000 \
  --env-file .env \
  macjarvis-backend

# 运行前端
docker run -d --name frontend \
  -p 80:80 \
  macjarvis-frontend
```

## 配置说明

### 环境变量

创建 `.env` 文件并配置以下变量：

```bash
# API 配置（使用 OpenRouter 或直接使用 OpenAI）
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-4o-mini

# 可选配置
OPENAI_TIMEOUT_S=60          # API 请求超时时间（秒）
OPENAI_MAX_TOOL_TURNS=8      # 最大工具调用轮数
```

### 支持的模型

系统支持以下模型（需要在 OpenRouter 或其他兼容 API 中使用）：

- `openai/gpt-4o-mini`
- `anthropic/claude-haiku-4.5`
- `google/gemini-2.5-flash`

### 路径安全限制

默认允许访问的目录：
- `~/` (用户主目录)
- `~/Desktop`
- `~/Documents`
- `~/Downloads`

如需修改，编辑 `src/agent/tools/validators.py` 中的 `ALLOWED_ROOTS` 列表。

## API 文档

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

## 开发指南

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
                    "param1": {"type": "string"}
                },
                "required": ["param1"]
            }
    
    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        # 实现工具逻辑
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

### 添加新模型

在 `src/agent/core/config.py` 中的 `ALLOWED_MODELS` 列表添加新模型：

```python
ALLOWED_MODELS = [
    # ... 现有模型
    "new-provider/new-model",
]
```

## 故障排查

### 后端无法启动

1. 检查 Python 版本：`python3 --version`（需要 3.12+）
2. 检查依赖安装：`pip list | grep fastapi`
3. 检查环境变量：确保 `.env` 文件存在且 `OPENAI_API_KEY` 已设置
4. 查看日志：检查控制台输出的错误信息

### 前端无法连接后端

1. 确认后端服务运行在 `http://localhost:8000`
2. 检查 CORS 配置（后端已配置允许所有来源）
3. 检查浏览器控制台的网络请求错误

### Docker 容器无法启动

1. 检查 Docker 服务状态：`docker ps`
2. 查看容器日志：`docker compose -f docker-compose.yml logs`
3. 检查环境变量文件：确保 `.env` 文件存在且格式正确
4. 检查端口占用：确保 8000 和 80 端口未被占用

## 安全注意事项

⚠️ **重要安全提示**：

1. **API Key 安全**：不要将 `.env` 文件提交到 Git 仓库
2. **路径限制**：系统已限制文件访问路径，请勿随意放宽限制
3. **命令执行**：工具会执行系统命令，请谨慎使用
4. **生产环境**：建议在生产环境中进一步限制工具权限

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 联系方式

- GitHub: [JNUZXF/MacJarvis](https://github.com/JNUZXF/MacJarvis)
- Issues: [GitHub Issues](https://github.com/JNUZXF/MacJarvis/issues)

## 更新日志

### v1.0.0 (2026-01-26)
- ✨ 初始版本发布
- ✨ 支持多模型切换（OpenAI、Anthropic、Google）
- ✨ 丰富的 macOS 系统管理工具
- ✨ 流式响应和实时工具调用显示
- ✨ Docker 容器化部署支持
- 🔒 路径访问安全限制
- 📝 完整的文档和示例
