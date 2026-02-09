#!/bin/bash
# File: restart.sh
# Purpose: 重启MacJarvis智能助手服务

set -e

# 颜色输出
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   重启 MacJarvis 服务${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 停止服务
./stop_prod.sh

echo ""
echo "等待3秒..."
sleep 3
echo ""

# 启动服务
./start_prod.sh
