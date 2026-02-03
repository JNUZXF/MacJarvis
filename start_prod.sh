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

# 检查并启动 Redis（如果已安装但未运行）
ensure_redis_running() {
    if ! command -v redis-cli &> /dev/null; then
        echo -e "${YELLOW}⚠${NC}  未检测到 redis-cli，跳过 Redis 启动检查"
        return 0
    fi

    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✓${NC} Redis 已运行"
        return 0
    fi

    echo -e "${YELLOW}检测到 Redis 未运行，尝试启动...${NC}"
    if command -v brew &> /dev/null; then
        brew services start redis &> /dev/null || true
    elif command -v redis-server &> /dev/null; then
        redis-server --daemonize yes &> /dev/null || true
    fi

    sleep 1
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✓${NC} Redis 启动成功"
        return 0
    fi

    echo -e "${YELLOW}⚠${NC} Redis 启动失败或未安装，后端将自动降级为内存缓存"
}

ensure_redis_running

# 后端准备
cd backend
if [ ! -d ".venv" ]; then
    echo -e "${RED}错误: 未找到后端虚拟环境，请先运行 ./start.sh${NC}"
    exit 1
fi
source .venv/bin/activate

# 检查关键依赖
echo -e "${BLUE}检查后端依赖...${NC}"
if ! python -c "import gunicorn" 2>/dev/null; then
    echo -e "${RED}✗ gunicorn 未安装${NC}"
    echo -e "${YELLOW}正在安装 gunicorn...${NC}"
    pip install gunicorn || {
        echo -e "${RED}gunicorn 安装失败，请手动执行: pip install gunicorn${NC}"
        exit 1
    }
fi

if ! python -c "import uvicorn" 2>/dev/null; then
    echo -e "${RED}✗ uvicorn 未安装${NC}"
    echo -e "${YELLOW}正在安装 uvicorn...${NC}"
    pip install uvicorn || {
        echo -e "${RED}uvicorn 安装失败，请手动执行: pip install uvicorn${NC}"
        exit 1
    }
fi

echo -e "${GREEN}✓${NC} 后端依赖检查通过"

# PostgreSQL 支持多 worker，SQLite 建议单 worker
WORKERS=2
if [ -n "${DATABASE_URL:-}" ] && [[ "${DATABASE_URL:-}" == sqlite* ]]; then
    WORKERS=1
    echo -e "${YELLOW}检测到SQLite数据库，后端将使用单worker启动以避免锁冲突${NC}"
    echo -e "${YELLOW}⚠${NC}  生产环境建议使用 PostgreSQL 以获得更好的并发性能"
fi

# 启动后端（Gunicorn）- 使用新的应用入口 app.main:app（包含聊天记录保存功能）
echo -e "${BLUE}启动后端服务（端口 $BACKEND_PORT）...${NC}"

# 使用虚拟环境中的gunicorn绝对路径
VENV_DIR="$SCRIPT_DIR/backend/.venv"
GUNICORN_PATH="$VENV_DIR/bin/gunicorn"

if [ ! -f "$GUNICORN_PATH" ]; then
    echo -e "${RED}✗ 无法找到gunicorn: $GUNICORN_PATH${NC}"
    echo -e "${YELLOW}尝试使用pip安装...${NC}"
    pip install gunicorn || exit 1
    if [ ! -f "$GUNICORN_PATH" ]; then
        echo -e "${RED}✗ gunicorn安装失败${NC}"
        exit 1
    fi
fi

# 使用绝对路径启动gunicorn，并确保Python环境正确
nohup "$GUNICORN_PATH" -k uvicorn.workers.UvicornWorker \
  app.main:app \
  -w "$WORKERS" \
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
export VITE_API_URL=http://127.0.0.1:$BACKEND_PORT
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

# 健康检查 - 等待后端真正启动
echo -e "${BLUE}等待后端服务启动...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0
BACKEND_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s -f http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        BACKEND_READY=true
        break
    fi
    
    # 检查进程是否还在运行
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${RED}✗ 后端进程意外退出${NC}"
        echo -e "${RED}最后10行错误日志:${NC}"
        tail -n 10 logs/backend_prod.log
        echo ""
        echo -e "${RED}完整日志请查看: logs/backend_prod.log${NC}"
        exit 1
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 1
done

echo ""

if [ "$BACKEND_READY" = true ]; then
    echo -e "${GREEN}✓${NC} 后端服务启动成功 (PID: $BACKEND_PID)"
    
    # 测试关键API端点
    echo -e "${BLUE}测试关键API端点...${NC}"
    
    # 测试 session init
    if curl -s -f -X POST http://localhost:$BACKEND_PORT/api/v1/session/init \
        -H "Content-Type: application/json" \
        -d '{"user_id":"health_check"}' > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Session API 正常"
    else
        echo -e "${YELLOW}⚠${NC}  Session API 响应异常（可能需要检查）"
    fi
    
    # 测试详细健康检查
    DETAILED_HEALTH=$(curl -s http://localhost:$BACKEND_PORT/health/detailed)
    if echo "$DETAILED_HEALTH" | grep -q '"status":"healthy"'; then
        echo -e "${GREEN}✓${NC} 所有组件健康"
    elif echo "$DETAILED_HEALTH" | grep -q '"status":"degraded"'; then
        echo -e "${YELLOW}⚠${NC}  部分组件降级运行"
        echo "$DETAILED_HEALTH" | python3 -m json.tool 2>/dev/null || echo "$DETAILED_HEALTH"
    else
        echo -e "${YELLOW}⚠${NC}  健康检查返回异常状态"
        echo "$DETAILED_HEALTH"
    fi
else
    echo -e "${RED}✗${NC} 后端服务启动超时（${MAX_RETRIES}秒）"
    echo -e "${RED}最后20行日志:${NC}"
    tail -n 20 logs/backend_prod.log
    echo ""
    echo -e "${RED}完整日志请查看: logs/backend_prod.log${NC}"
    
    # 清理失败的进程
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    exit 1
fi

# 前后端连通性测试
echo ""
echo -e "${BLUE}执行前后端连通性测试...${NC}"
if [ -f "scripts/test_frontend_backend_connectivity.sh" ]; then
    chmod +x scripts/test_frontend_backend_connectivity.sh
    if bash scripts/test_frontend_backend_connectivity.sh "http://127.0.0.1:$BACKEND_PORT" "http://localhost:$FRONTEND_PORT"; then
        echo ""
        echo -e "${GREEN}================================${NC}"
        echo -e "${GREEN}   🎉 生产模式启动成功！${NC}"
        echo -e "${GREEN}================================${NC}"
        echo ""
        echo -e "访问地址:"
        echo -e "  前端界面: ${BLUE}http://localhost:$FRONTEND_PORT${NC}"
        echo -e "  后端API:  ${BLUE}http://localhost:$BACKEND_PORT${NC}"
        echo ""
        echo -e "管理命令:"
        echo -e "  查看日志: ${BLUE}tail -f logs/backend_prod.log${NC}"
        echo -e "  停止服务: ${BLUE}./stop_prod.sh${NC}"
        echo ""
    else
        echo ""
        echo -e "${RED}================================${NC}"
        echo -e "${RED}   ⚠️  启动完成但连通性测试失败${NC}"
        echo -e "${RED}================================${NC}"
        echo ""
        echo -e "${YELLOW}服务已启动，但前后端连通性存在问题${NC}"
        echo -e "${YELLOW}请检查上述测试失败的原因${NC}"
        echo ""
        echo -e "访问地址:"
        echo -e "  前端界面: ${BLUE}http://localhost:$FRONTEND_PORT${NC}"
        echo -e "  后端API:  ${BLUE}http://localhost:$BACKEND_PORT${NC}"
        echo ""
        echo -e "排查建议:"
        echo -e "  1. 查看后端日志: ${BLUE}tail -f logs/backend_prod.log${NC}"
        echo -e "  2. 手动测试后端: ${BLUE}curl http://localhost:$BACKEND_PORT/health${NC}"
        echo -e "  3. 检查CORS配置: ${BLUE}cat backend/.env | grep CORS${NC}"
        echo ""
        exit 1
    fi
else
    echo -e "${YELLOW}⚠${NC}  连通性测试脚本未找到，跳过测试"
    echo ""
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}   🎉 生产模式启动成功！${NC}"
    echo -e "${GREEN}================================${NC}"
    echo ""
    echo -e "访问地址:"
    echo -e "  前端界面: ${BLUE}http://localhost:$FRONTEND_PORT${NC}"
    echo -e "  后端API:  ${BLUE}http://localhost:$BACKEND_PORT${NC}"
    echo ""
fi
