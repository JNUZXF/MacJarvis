#!/bin/bash
# File: start_prod.sh
# Purpose: 启动MacJarvis智能助手（生产模式）

set -Eeuo pipefail

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 端口配置
BACKEND_PORT=${BACKEND_PORT:-18888}
FRONTEND_PORT=${FRONTEND_PORT:-18889}
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_DIR="$SCRIPT_DIR/logs"
BACKEND_PID_FILE="$LOG_DIR/backend_prod.pid"
NGINX_TEMPLATE="$SCRIPT_DIR/nginx/mac_agent.conf.template"
NGINX_GENERATED_CONF="$LOG_DIR/nginx.runtime.conf"

fail() {
    echo -e "${RED}错误: $1${NC}"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

info() {
    echo -e "${BLUE}$1${NC}"
}

ok() {
    echo -e "${GREEN}✓${NC} $1"
}

check_port_free() {
    local port="$1"
    local usage
    usage=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
    if [ -n "$usage" ]; then
        echo "$usage"
        fail "端口 $port 已被占用。请先释放端口，或修改 BACKEND_PORT/FRONTEND_PORT。"
    fi
}

cd "$SCRIPT_DIR"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   MacJarvis 生产模式启动器${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 检查依赖命令
if ! command -v python3 &> /dev/null; then
    fail "未找到 Python3"
fi
if ! command -v node &> /dev/null; then
    fail "未找到 Node.js"
fi

# 检查.env
if [ ! -f ".env" ]; then
    fail "未找到 .env 文件，请先配置 API 密钥"
fi

# 创建日志目录
mkdir -p "$LOG_DIR"

# 避免重复启动
if [ -f "$BACKEND_PID_FILE" ]; then
    BACKEND_PID=$(cat "$BACKEND_PID_FILE" 2>/dev/null || true)
    if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        fail "检测到后端已在运行 (PID: $BACKEND_PID)，请先执行 ./stop_prod.sh"
    fi
    rm -f "$BACKEND_PID_FILE"
fi

# 启动前检查端口占用，避免误杀无关进程
check_port_free "$BACKEND_PORT"
check_port_free "$FRONTEND_PORT"

# 检查并启动 Redis（如果已安装但未运行）
ensure_redis_running() {
    if ! command -v redis-cli &> /dev/null; then
        warn "未检测到 redis-cli，跳过 Redis 启动检查"
        return 0
    fi

    if redis-cli ping &> /dev/null; then
        ok "Redis 已运行"
        return 0
    fi

    info "检测到 Redis 未运行，尝试启动..."
    if command -v brew &> /dev/null; then
        brew services start redis &> /dev/null || true
    elif command -v redis-server &> /dev/null; then
        redis-server --daemonize yes &> /dev/null || true
    fi

    sleep 1
    if redis-cli ping &> /dev/null; then
        ok "Redis 启动成功"
        return 0
    fi

    warn "Redis 启动失败或未安装，后端将自动降级为内存缓存"
}

ensure_redis_running

# 后端准备
cd backend
if [ ! -d ".venv" ]; then
    fail "未找到后端虚拟环境 backend/.venv"
fi
source .venv/bin/activate

# 检查关键依赖
info "检查后端依赖..."
if ! python -c "import gunicorn" 2>/dev/null; then
    fail "后端依赖缺失: gunicorn（请先在 backend/.venv 安装依赖）"
fi

if ! python -c "import uvicorn" 2>/dev/null; then
    fail "后端依赖缺失: uvicorn（请先在 backend/.venv 安装依赖）"
fi

ok "后端依赖检查通过"

# PostgreSQL 支持多 worker，SQLite（含默认回退）使用单 worker，避免锁冲突
WORKERS=2
if [ -z "${DATABASE_URL:-}" ] || [[ "${DATABASE_URL:-}" == sqlite* ]]; then
    WORKERS=1
    warn "使用 SQLite（或默认 SQLite 回退），后端将使用单 worker 启动"
    warn "生产环境建议配置 PostgreSQL 以提升并发性能"
fi

# 启动后端（Gunicorn）- 使用新的应用入口 app.main:app（包含聊天记录保存功能）
info "启动后端服务（端口 ${BACKEND_PORT}）..."

# 使用虚拟环境中的gunicorn绝对路径
VENV_DIR="$SCRIPT_DIR/backend/.venv"
GUNICORN_PATH="$VENV_DIR/bin/gunicorn"

if [ ! -f "$GUNICORN_PATH" ]; then
    fail "无法找到 gunicorn 可执行文件: $GUNICORN_PATH"
fi

# 使用绝对路径启动gunicorn，并确保Python环境正确
nohup "$GUNICORN_PATH" -k uvicorn.workers.UvicornWorker \
  app.main:app \
  -w "$WORKERS" \
  -b 0.0.0.0:$BACKEND_PORT \
  --access-logfile "$LOG_DIR/backend_access.log" \
  --error-logfile "$LOG_DIR/backend_error.log" \
  > "$LOG_DIR/backend_prod.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$BACKEND_PID_FILE"
cd ..

# 前端构建
info "构建前端静态资源..."
cd frontend
if [ ! -d "node_modules" ]; then
    fail "前端依赖缺失: frontend/node_modules（请先执行 cd frontend && npm ci）"
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
    info "启动 Nginx（端口 ${FRONTEND_PORT}）..."

    if [ ! -f "$NGINX_TEMPLATE" ]; then
        fail "未找到 Nginx 模板: $NGINX_TEMPLATE"
    fi

    sed \
      -e "s|__FRONTEND_PORT__|${FRONTEND_PORT}|g" \
      -e "s|__BACKEND_PORT__|${BACKEND_PORT}|g" \
      -e "s|__FRONTEND_DIST__|$SCRIPT_DIR/frontend/dist|g" \
      "$NGINX_TEMPLATE" > "$NGINX_GENERATED_CONF"

    "$NGINX_CMD" -s stop -p "$SCRIPT_DIR" 2>/dev/null || true
    "$NGINX_CMD" -c "$NGINX_GENERATED_CONF" -p "$SCRIPT_DIR"
else
    warn "未检测到 Nginx，请先安装并确保命令可用"
fi

# 健康检查 - 等待后端真正启动
info "等待后端服务启动..."
MAX_RETRIES=30
RETRY_COUNT=0
BACKEND_READY=false

while [ "$RETRY_COUNT" -lt "$MAX_RETRIES" ]; do
    if curl -s -f "http://localhost:${BACKEND_PORT}/health" > /dev/null 2>&1; then
        BACKEND_READY=true
        break
    fi
    
    # 检查进程是否还在运行
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo -e "${RED}✗ 后端进程意外退出${NC}"
        echo -e "${RED}最后10行错误日志:${NC}"
        tail -n 10 "$LOG_DIR/backend_prod.log"
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
    echo -e "${GREEN}✓${NC} 后端服务启动成功 (PID: ${BACKEND_PID})"
    
    # 测试关键API端点
    echo -e "${BLUE}测试关键API端点...${NC}"
    
    # 测试 session init
    if curl -s -f -X POST "http://localhost:${BACKEND_PORT}/api/v1/session/init" \
        -H "Content-Type: application/json" \
        -d '{"user_id":"health_check"}' > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Session API 正常"
    else
        echo -e "${YELLOW}⚠${NC}  Session API 响应异常（可能需要检查）"
    fi
    
    # 测试详细健康检查
    DETAILED_HEALTH=$(curl -s "http://localhost:${BACKEND_PORT}/health/detailed" || true)
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
    tail -n 20 "$LOG_DIR/backend_prod.log"
    echo ""
    echo -e "${RED}完整日志请查看: logs/backend_prod.log${NC}"
    
    # 清理失败的进程
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    
    exit 1
fi

# 前后端连通性测试
echo ""
echo -e "${BLUE}执行前后端连通性测试...${NC}"
if [ -f "scripts/test_frontend_backend_connectivity.sh" ]; then
    chmod +x scripts/test_frontend_backend_connectivity.sh
    if bash scripts/test_frontend_backend_connectivity.sh "http://127.0.0.1:${BACKEND_PORT}" "http://localhost:${FRONTEND_PORT}"; then
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
