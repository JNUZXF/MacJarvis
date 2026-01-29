#!/bin/bash
# File: stop_prod.sh
# Purpose: 停止MacJarvis智能助手（生产模式）

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   停止 MacJarvis 生产服务${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 停止后端服务
if [ -f "logs/backend_prod.pid" ]; then
    BACKEND_PID=$(cat logs/backend_prod.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}停止后端服务 (PID: $BACKEND_PID)...${NC}"
        kill $BACKEND_PID
        echo -e "${GREEN}✓${NC} 后端服务已停止"
    else
        echo -e "${YELLOW}⚠${NC}  后端服务未运行"
    fi
    rm -f logs/backend_prod.pid
else
    echo -e "${YELLOW}⚠${NC}  未找到后端PID文件"
fi

# 停止 Nginx（如果可用）
if command -v nginx &> /dev/null; then
    echo -e "${YELLOW}停止Nginx...${NC}"
    nginx -s stop -p "$SCRIPT_DIR" 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Nginx已停止"
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}   生产服务已停止${NC}"
echo -e "${GREEN}================================${NC}"
