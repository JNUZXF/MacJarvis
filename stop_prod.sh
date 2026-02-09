#!/bin/bash
# File: stop_prod.sh
# Purpose: 停止MacJarvis智能助手（生产模式）

set -Eeuo pipefail

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"
LOG_DIR="$SCRIPT_DIR/logs"
BACKEND_PID_FILE="$LOG_DIR/backend_prod.pid"
BACKEND_PORT=${BACKEND_PORT:-18888}
FRONTEND_PORT=${FRONTEND_PORT:-18889}

kill_port_listener_if_expected() {
    local port="$1"
    local pids
    pids=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)
    if [ -z "$pids" ]; then
        return 0
    fi

    while read -r pid; do
        [ -z "$pid" ] && continue
        echo -e "${YELLOW}清理端口 $port 残留进程 (PID: $pid)...${NC}"
        kill "$pid" 2>/dev/null || true
    done <<< "$pids"
}

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   停止 MacJarvis 生产服务${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 停止后端服务
if [ -f "$BACKEND_PID_FILE" ]; then
    BACKEND_PID=$(cat "$BACKEND_PID_FILE")
    if ps -p "$BACKEND_PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}停止后端服务 (PID: $BACKEND_PID)...${NC}"
        kill "$BACKEND_PID" 2>/dev/null || true
        for _ in {1..10}; do
            if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            echo -e "${YELLOW}后端未在10秒内退出，发送 SIGKILL...${NC}"
            kill -9 "$BACKEND_PID" 2>/dev/null || true
        fi
        echo -e "${GREEN}✓${NC} 后端服务已停止"
    else
        echo -e "${YELLOW}⚠${NC}  后端服务未运行"
    fi
    rm -f "$BACKEND_PID_FILE"
else
    echo -e "${YELLOW}⚠${NC}  未找到后端PID文件"
fi

# 停止 Nginx（如果可用）
NGINX_CMD=""
if command -v nginx &> /dev/null; then
    NGINX_CMD="$(command -v nginx)"
elif [ -x "/opt/homebrew/bin/nginx" ]; then
    NGINX_CMD="/opt/homebrew/bin/nginx"
elif [ -x "/usr/local/bin/nginx" ]; then
    NGINX_CMD="/usr/local/bin/nginx"
fi

if [ -n "$NGINX_CMD" ]; then
    echo -e "${YELLOW}停止Nginx...${NC}"
    "$NGINX_CMD" -s stop -p "$SCRIPT_DIR" 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Nginx已停止"
fi

# 兜底清理端口残留进程
kill_port_listener_if_expected "$BACKEND_PORT"
kill_port_listener_if_expected "$FRONTEND_PORT"

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}   生产服务已停止${NC}"
echo -e "${GREEN}================================${NC}"
