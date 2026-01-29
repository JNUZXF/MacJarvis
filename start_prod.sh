#!/bin/bash
# File: start_prod.sh
# Purpose: 启动MacJarvis智能助手（生产模式）

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 端口配置
BACKEND_PORT=${BACKEND_PORT:-18888}
FRONTEND_PORT=${FRONTEND_PORT:-18889}

# 启动前释放端口，避免残留进程占用
release_port() {
    local port="$1"
    local pids
    pids=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}检测到端口 ${port} 被占用，正在释放...${NC}"
        while read -r pid; do
            if [ -n "$pid" ]; then
                kill "$pid" 2>/dev/null || true
            fi
        done <<< "$pids"
        sleep 1
    fi
}

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   MacJarvis 生产模式启动器${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 释放端口，确保本应用占用指定端口
release_port "$BACKEND_PORT"
release_port "$FRONTEND_PORT"

# 检查依赖命令
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到Python3${NC}"
    exit 1
fi
if ! command -v node &> /dev/null; then
    echo -e "${RED}错误: 未找到Node.js${NC}"
    exit 1
fi

# 检查.env
if [ ! -f ".env" ]; then
    echo -e "${RED}错误: 未找到.env文件，请先配置API密钥${NC}"
    exit 1
fi

# 创建日志目录
mkdir -p logs

# 后端准备
cd backend
if [ ! -d ".venv" ]; then
    echo -e "${RED}错误: 未找到后端虚拟环境，请先运行 ./start.sh${NC}"
    exit 1
fi
source .venv/bin/activate

# 启动后端（Gunicorn）- 使用新的应用入口 app.main:app（包含聊天记录保存功能）
echo -e "${BLUE}启动后端服务（端口 $BACKEND_PORT）...${NC}"
nohup gunicorn -k uvicorn.workers.UvicornWorker \
  app.main:app \
  -w 2 \
  -b 0.0.0.0:$BACKEND_PORT \
  --access-logfile ../logs/backend_access.log \
  --error-logfile ../logs/backend_error.log \
  > ../logs/backend_prod.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../logs/backend_prod.pid
cd ..

# 前端构建
echo -e "${BLUE}构建前端静态资源...${NC}"
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
fi
export VITE_API_URL=http://localhost:$BACKEND_PORT
npm run build
cd ..

# 启动 Nginx（如果可用）
NGINX_CMD=""
if command -v nginx &> /dev/null; then
    NGINX_CMD="$(command -v nginx)"
elif [ -x "/opt/homebrew/bin/nginx" ]; then
    NGINX_CMD="/opt/homebrew/bin/nginx"
elif [ -x "/usr/local/bin/nginx" ]; then
    NGINX_CMD="/usr/local/bin/nginx"
fi

if [ -n "$NGINX_CMD" ]; then
    echo -e "${BLUE}启动Nginx（端口 $FRONTEND_PORT）...${NC}"
    "$NGINX_CMD" -c "$SCRIPT_DIR/nginx/mac_agent.conf" -p "$SCRIPT_DIR" || true
else
    echo -e "${YELLOW}⚠${NC}  未检测到nginx，请手动安装并启动"
fi

# 健康检查
sleep 3
if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} 后端服务启动成功 (PID: $BACKEND_PID)"
else
    echo -e "${RED}✗${NC} 后端服务启动失败，请查看 logs/backend_prod.log"
    exit 1
fi

# 输出访问地址
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}   🎉 生产模式启动成功！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "访问地址:"
echo -e "  前端界面: ${BLUE}http://localhost:$FRONTEND_PORT${NC}"
echo -e "  后端API:  ${BLUE}http://localhost:$BACKEND_PORT${NC}"
echo ""
