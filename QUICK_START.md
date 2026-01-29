# MacJarvis 快速启动指南（本地部署版）

## 📋 前置要求

在开始之前，请确保你的Mac已安装以下软件：

- **Python 3.12+** - [下载地址](https://www.python.org/downloads/)
- **Node.js 18+** - [下载地址](https://nodejs.org/)
- **Git** - 通常macOS已预装

检查是否已安装：
```bash
python3 --version
node --version
git --version
```

## 🚀 快速启动

### 1. 配置API密钥

首次使用需要配置OpenRouter API密钥：

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入你的API密钥
nano .env
```

在`.env`文件中修改以下内容：
```bash
OPENROUTER_API_KEY=your-actual-api-key-here
```

> 💡 获取API密钥：访问 [OpenRouter](https://openrouter.ai/) 注册并获取API密钥

### 2. 启动服务

运行启动脚本：
```bash
./start.sh
```

启动脚本会自动：
- ✅ 检查Python和Node.js环境
- ✅ 创建Python虚拟环境
- ✅ 安装后端依赖（首次运行）
- ✅ 安装前端依赖（首次运行）
- ✅ 启动后端服务（端口8000）
- ✅ 启动前端服务（端口5173）
- ✅ 自动打开浏览器

### 3. 访问界面

启动成功后，浏览器会自动打开：
- **前端界面**: http://localhost:5173
- **后端API**: http://localhost:8000

## 🛠️ 常用命令

### 停止服务
```bash
./stop.sh
```

### 重启服务
```bash
./restart.sh
```

### 查看日志
```bash
# 查看后端日志
tail -f logs/backend.log

# 查看前端日志
tail -f logs/frontend.log
```

### 手动启动（开发模式）

如果需要手动启动服务（方便调试）：

**启动后端：**
```bash
cd backend
source .venv/bin/activate
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```

**启动前端（新终端窗口）：**
```bash
cd frontend
npm run dev
```

## 📁 项目结构

```
mac_agent/
├── backend/              # 后端代码
│   ├── agent/           # Agent核心逻辑
│   ├── server/          # FastAPI服务器
│   ├── .venv/           # Python虚拟环境
│   └── requirements.txt # Python依赖
├── frontend/            # 前端代码
│   ├── src/            # React源代码
│   └── package.json    # Node.js依赖
├── logs/               # 日志文件
├── .env                # 环境变量配置
├── start.sh            # 启动脚本
├── stop.sh             # 停止脚本
└── restart.sh          # 重启脚本
```

## 🔧 配置说明

### 环境变量（.env文件）

```bash
# OpenRouter API配置
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# 默认模型
DEFAULT_MODEL=anthropic/claude-3.5-haiku

# 日志级别
LOG_LEVEL=INFO

# 内存管理配置
MEMORY_WINDOW_SIZE=10
MEMORY_TTL_S=3600
MEMORY_CONTEXT_MAX_CHARS=4000
MEMORY_SUMMARY_TRIGGER=24
MEMORY_KEEP_LAST=8

# 附件处理
ATTACHMENT_TEXT_LIMIT=10000
```

### 修改端口

如果默认端口被占用，可以修改：

**后端端口（默认8000）：**
编辑 `start.sh`，修改：
```bash
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```

**前端端口（默认5173）：**
编辑 `frontend/vite.config.ts`：
```typescript
export default defineConfig({
  server: {
    port: 5173,  // 修改为其他端口
  }
})
```

## 🐛 故障排查

### 问题1: 后端启动失败

**检查日志：**
```bash
cat logs/backend.log
```

**常见原因：**
- API密钥未配置或错误
- 端口8000被占用
- Python依赖未安装

**解决方法：**
```bash
# 重新安装依赖
cd backend
source .venv/bin/activate
pip install -r requirements.txt

# 检查端口占用
lsof -i :8000
```

### 问题2: 前端启动失败

**检查日志：**
```bash
cat logs/frontend.log
```

**常见原因：**
- Node.js依赖未安装
- 端口5173被占用

**解决方法：**
```bash
# 重新安装依赖
cd frontend
rm -rf node_modules package-lock.json
npm install

# 检查端口占用
lsof -i :5173
```

### 问题3: 无法连接后端

**检查后端健康状态：**
```bash
curl http://localhost:8000/health
```

应该返回：
```json
{"status":"ok","service":"macjarvis-backend"}
```

**检查前端配置：**
确保 `frontend/src/App.tsx` 中的API地址正确：
```typescript
const API_BASE = 'http://localhost:8000';
```

### 问题4: 工具调用失败

**检查系统权限：**
某些macOS工具需要系统权限，首次使用可能需要授权：
- 文件访问权限
- 辅助功能权限（截屏、剪贴板）
- 网络访问权限

**检查路径配置：**
在前端界面中配置允许访问的路径：
- 设置 → 路径配置
- 添加需要访问的目录（如 ~/Desktop, ~/Documents）

## 🔐 安全注意事项

1. **API密钥保护**：
   - 不要将`.env`文件提交到Git仓库
   - 定期更换API密钥
   - 不要在公共场合分享密钥

2. **路径访问限制**：
   - 只配置必要的访问路径
   - 避免授权根目录（/）访问
   - 定期检查路径配置

3. **网络安全**：
   - 默认只监听本地（localhost）
   - 如需远程访问，请配置防火墙
   - 使用HTTPS（生产环境）

## 📚 更多文档

- [完整README](./README.md) - 详细的项目文档
- [API文档](./docs/) - 后端API接口说明
- [开发指南](./docs/) - 开发和贡献指南

## 💡 使用技巧

1. **快速搜索文件**：
   - "帮我在桌面找所有PDF文件"
   - "搜索Documents目录下包含'报告'的文件"

2. **系统监控**：
   - "查看当前CPU和内存使用情况"
   - "列出占用资源最多的进程"

3. **文件管理**：
   - "读取桌面上的README.md文件"
   - "在Downloads创建一个新文件夹"

4. **应用管理**：
   - "打开Chrome浏览器"
   - "列出所有已安装的应用"

5. **网络诊断**：
   - "检查网络连接状态"
   - "查看当前监听的端口"

## 🆘 获取帮助

如果遇到问题：
1. 查看日志文件（`logs/backend.log` 和 `logs/frontend.log`）
2. 检查本文档的故障排查部分
3. 查看完整README中的详细说明
4. 提交Issue到GitHub仓库

---

**祝你使用愉快！** 🎉
