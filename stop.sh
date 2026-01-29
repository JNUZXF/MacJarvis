#!/bin/bash
# File: stop.sh
# Purpose: 停止MacJarvis智能助手服务

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   停止 MacJarvis 服务${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 停止后端服务
if [ -f "logs/backend.pid" ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}停止后端服务 (PID: $BACKEND_PID)...${NC}"
        kill $BACKEND_PID
        echo -e "${GREEN}✓${NC} 后端服务已停止"
    else
        echo -e "${YELLOW}⚠${NC}  后端服务未运行"
    fi
    rm logs/backend.pid
else
    echo -e "${YELLOW}⚠${NC}  未找到后端PID文件"
fi

# 停止前端服务
if [ -f "logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}停止前端服务 (PID: $FRONTEND_PID)...${NC}"
        kill $FRONTEND_PID
        echo -e "${GREEN}✓${NC} 前端服务已停止"
    else
        echo -e "${YELLOW}⚠${NC}  前端服务未运行"
    fi
    rm logs/frontend.pid
else
    echo -e "${YELLOW}⚠${NC}  未找到前端PID文件"
fi

# 清理可能残留的进程
echo ""
echo -e "${YELLOW}清理残留进程...${NC}"

# 查找并终止uvicorn进程
UVICORN_PIDS=$(pgrep -f "uvicorn server.app:app" || true)
if [ ! -z "$UVICORN_PIDS" ]; then
    echo "  终止uvicorn进程: $UVICORN_PIDS"
    kill $UVICORN_PIDS 2>/dev/null || true
fi

# 查找并终止vite进程
VITE_PIDS=$(pgrep -f "vite" || true)
if [ ! -z "$VITE_PIDS" ]; then
    echo "  终止vite进程: $VITE_PIDS"
    kill $VITE_PIDS 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}   所有服务已停止${NC}"
echo -e "${GREEN}================================${NC}"
