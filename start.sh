#!/bin/bash
# File: start.sh
# Purpose: 启动MacJarvis智能助手（本地部署版本）

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   MacJarvis 智能助手启动器${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查Python版本
echo -e "${YELLOW}[1/6]${NC} 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到Python3，请先安装Python 3.12+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}✓${NC} Python版本: $PYTHON_VERSION"

# 检查Node.js版本
echo -e "${YELLOW}[2/6]${NC} 检查Node.js环境..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}错误: 未找到Node.js，请先安装Node.js 18+${NC}"
    exit 1
fi

NODE_VERSION=$(node -v)
echo -e "${GREEN}✓${NC} Node.js版本: $NODE_VERSION"

# 检查并创建后端虚拟环境
echo -e "${YELLOW}[3/6]${NC} 设置后端环境..."
cd backend

if [ ! -d ".venv" ]; then
    echo "  创建Python虚拟环境..."
    python3 -m venv .venv
fi

echo "  激活虚拟环境..."
source .venv/bin/activate

# 智能检查是否需要安装依赖
NEED_INSTALL=false

if [ ! -f ".venv/.deps_installed" ]; then
    # 首次安装
    NEED_INSTALL=true
elif [ ! -f ".venv/.deps_timestamp" ]; then
    # 时间戳文件丢失，重新安装
    NEED_INSTALL=true
else
    # 检查requirements.txt是否更新
    REQ_TIME=$(stat -f "%m" requirements.txt 2>/dev/null || stat -c "%Y" requirements.txt 2>/dev/null || echo "0")
    INSTALLED_TIME=$(cat .venv/.deps_timestamp 2>/dev/null || echo "0")
    
    if [ "$REQ_TIME" -gt "$INSTALLED_TIME" ]; then
        echo "  检测到requirements.txt已更新，需要重新安装依赖..."
        NEED_INSTALL=true
    fi
fi

if [ "$NEED_INSTALL" = true ]; then
    echo "  安装/更新依赖..."
    pip install --upgrade pip > /dev/null 2>&1
    pip install -r requirements.txt
    touch .venv/.deps_installed
    # 记录安装时间戳
    stat -f "%m" requirements.txt > .venv/.deps_timestamp 2>/dev/null || stat -c "%Y" requirements.txt > .venv/.deps_timestamp 2>/dev/null || date +%s > .venv/.deps_timestamp
    echo -e "${GREEN}✓${NC} 后端依赖安装完成"
else
    echo -e "${GREEN}✓${NC} 后端依赖已安装（使用缓存）"
fi

cd ..

# 检查并安装前端依赖
echo -e "${YELLOW}[4/6]${NC} 设置前端环境..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "  安装前端依赖..."
    npm install
    echo -e "${GREEN}✓${NC} 前端依赖安装完成"
else
    echo -e "${GREEN}✓${NC} 前端依赖已安装"
fi

cd ..

# 检查环境变量配置
echo -e "${YELLOW}[5/6]${NC} 检查配置文件..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}⚠${NC}  未找到.env文件，从.env.example创建..."
        cp .env.example .env
        echo -e "${RED}请编辑 .env 文件，填入你的OpenRouter API密钥${NC}"
        echo -e "${RED}然后重新运行此脚本${NC}"
        exit 1
    else
        echo -e "${RED}错误: 未找到.env.example文件${NC}"
        exit 1
    fi
fi

# 检查API密钥是否配置（支持带引号和不带引号的情况）
# 检查示例密钥
if grep -qE "(your-openrouter-api-key-here|your-openai-api-key-here|sk-proj-1234567890)" .env 2>/dev/null; then
    echo -e "${YELLOW}⚠${NC}  检测到.env文件中可能包含示例API密钥"
    echo -e "${YELLOW}⚠${NC}  请确保已配置正确的OpenRouter API密钥或OpenAI API密钥"
fi

# 检查是否至少有一个有效的API密钥配置（支持带引号和不带引号）
# 匹配模式: OPENROUTER_API_KEY="sk-..." 或 OPENROUTER_API_KEY=sk-...
# 排除示例密钥: sk-proj-1234567890, your-*-api-key-here
HAS_VALID_KEY=false

# 检查OPENROUTER_API_KEY（排除示例密钥，要求至少30个字符的密钥）
if grep -E '^[[:space:]]*OPENROUTER_API_KEY[[:space:]]*=' .env 2>/dev/null | grep -vE '(your-openrouter-api-key-here|sk-proj-1234567890)' | grep -qE 'sk-[a-zA-Z0-9_-]{30,}'; then
    HAS_VALID_KEY=true
fi

# 检查OPENAI_API_KEY（排除示例密钥，要求至少30个字符的密钥）
if [ "$HAS_VALID_KEY" = false ]; then
    if grep -E '^[[:space:]]*OPENAI_API_KEY[[:space:]]*=' .env 2>/dev/null | grep -vE '(your-openai-api-key-here|sk-proj-1234567890)' | grep -qE 'sk-[a-zA-Z0-9_-]{30,}'; then
        HAS_VALID_KEY=true
    fi
fi

if [ "$HAS_VALID_KEY" = false ]; then
    echo -e "${RED}错误: 请在.env文件中配置OPENROUTER_API_KEY或OPENAI_API_KEY${NC}"
    echo -e "${RED}提示: API密钥应以 'sk-' 开头，可以带引号或不带引号${NC}"
    echo -e "${RED}当前.env文件内容:${NC}"
    grep -E '^(OPENROUTER_API_KEY|OPENAI_API_KEY)=' .env 2>/dev/null | sed 's/=.*/=***/' || echo "  未找到API密钥配置"
    exit 1
fi

echo -e "${GREEN}✓${NC} 配置文件检查完成"

# 启动服务
echo -e "${YELLOW}[6/6]${NC} 启动服务..."
echo ""

# 创建日志目录
mkdir -p logs

# 配置端口（避免冲突）
BACKEND_PORT=18888
FRONTEND_PORT=18889

# 启动后端服务
echo -e "${BLUE}启动后端服务（端口 $BACKEND_PORT）...${NC}"
cd backend
source .venv/bin/activate

# 确保关键依赖已安装（快速检查）
if ! python -c "import dotenv" 2>/dev/null; then
    echo "  安装python-dotenv..."
    pip install python-dotenv > /dev/null 2>&1
fi
if ! python -c "import multipart" 2>/dev/null; then
    echo "  安装python-multipart..."
    pip install python-multipart > /dev/null 2>&1
fi

# 启动服务（环境变量会通过python-dotenv自动加载）
nohup python -m uvicorn server.app:app --host 0.0.0.0 --port $BACKEND_PORT --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../logs/backend.pid
cd ..

# 等待后端启动
echo "  等待后端服务启动..."
sleep 3

# 检查后端是否启动成功
if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} 后端服务启动成功 (PID: $BACKEND_PID, 端口: $BACKEND_PORT)"
else
    echo -e "${RED}✗${NC} 后端服务启动失败，请查看 logs/backend.log"
    exit 1
fi

# 启动前端服务
echo -e "${BLUE}启动前端服务（端口 $FRONTEND_PORT）...${NC}"
cd frontend
# 设置API URL环境变量
export VITE_API_URL=http://localhost:$BACKEND_PORT
nohup npm run dev -- --port $FRONTEND_PORT > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../logs/frontend.pid
cd ..

# 等待前端启动
echo "  等待前端服务启动..."
sleep 5

# 检查前端是否启动成功
if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} 前端服务启动成功 (PID: $FRONTEND_PID, 端口: $FRONTEND_PORT)"
else
    echo -e "${YELLOW}⚠${NC}  前端服务可能需要更多时间启动，请稍候..."
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}   🎉 MacJarvis 启动成功！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "访问地址:"
echo -e "  前端界面: ${BLUE}http://localhost:$FRONTEND_PORT${NC}"
echo -e "  后端API:  ${BLUE}http://localhost:$BACKEND_PORT${NC}"
echo ""
echo -e "日志文件:"
echo -e "  后端: ${BLUE}logs/backend.log${NC}"
echo -e "  前端: ${BLUE}logs/frontend.log${NC}"
echo ""
echo -e "停止服务:"
echo -e "  运行: ${BLUE}./stop.sh${NC}"
echo ""
echo -e "查看日志:"
echo -e "  后端: ${BLUE}tail -f logs/backend.log${NC}"
echo -e "  前端: ${BLUE}tail -f logs/frontend.log${NC}"
echo ""

# 自动打开浏览器（可选）
if command -v open &> /dev/null; then
    echo -e "${YELLOW}5秒后将自动打开浏览器...${NC}"
    sleep 5
    open http://localhost:$FRONTEND_PORT
fi
