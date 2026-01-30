#!/bin/bash
# File: scripts/setup_postgresql.sh
# Purpose: 快速设置 PostgreSQL 数据库（macOS）

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   PostgreSQL 快速设置脚本${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 检查是否安装了 Homebrew
if ! command -v brew &> /dev/null; then
    echo -e "${RED}错误: 未找到 Homebrew${NC}"
    echo -e "${YELLOW}请先安装 Homebrew: https://brew.sh/${NC}"
    exit 1
fi

# 添加 PostgreSQL 到 PATH（如果使用 Homebrew）
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"

# 检查 PostgreSQL 是否已安装
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}检测到 PostgreSQL 未安装，开始安装...${NC}"
    brew install postgresql@15
    
    echo -e "${GREEN}✓${NC} PostgreSQL 安装完成"
else
    echo -e "${GREEN}✓${NC} PostgreSQL 已安装"
    psql --version
fi

# 启动 PostgreSQL 服务
echo ""
echo -e "${BLUE}启动 PostgreSQL 服务...${NC}"

# 检查并配置端口为 5433（避免与 Cursor 编辑器冲突）
PG_CONFIG="/opt/homebrew/var/postgresql@15/postgresql.conf"
if [ -f "$PG_CONFIG" ]; then
    # 检查端口是否已配置为 5433
    if ! grep -q "^port = 5433" "$PG_CONFIG"; then
        echo -e "${YELLOW}配置 PostgreSQL 端口为 5433...${NC}"
        brew services stop postgresql@15 &>/dev/null || true
        sleep 1
        # 备份配置文件
        cp "$PG_CONFIG" "${PG_CONFIG}.bak"
        # 修改端口配置
        sed -i.bak 's/^#port = 5432/port = 5433/' "$PG_CONFIG"
        sed -i.bak 's/^port = 5432/port = 5433/' "$PG_CONFIG"
        echo -e "${GREEN}✓${NC} 端口已配置为 5433"
    fi
fi

if brew services list | grep -q "postgresql@15.*started"; then
    echo -e "${GREEN}✓${NC} PostgreSQL 服务已在运行（端口 5433）"
else
    brew services start postgresql@15
    sleep 3
    if brew services list | grep -q "postgresql@15.*started"; then
        echo -e "${GREEN}✓${NC} PostgreSQL 服务启动成功（端口 5433）"
    else
        echo -e "${RED}✗${NC} PostgreSQL 服务启动失败"
        echo -e "${YELLOW}请检查日志: tail -50 /opt/homebrew/var/log/postgresql@15.log${NC}"
        exit 1
    fi
fi

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo ""
    echo -e "${YELLOW}检测到 .env 文件不存在，从 .env.example 创建...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓${NC} .env 文件已创建"
fi

# 创建数据库
echo ""
echo -e "${BLUE}创建数据库...${NC}"

# 尝试使用 postgres 用户连接（Postgres.app 默认）
# 使用端口 5433 以避免冲突
DB_EXISTS=$(psql -U postgres -p 5433 -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw mac_agent && echo "yes" || echo "no")

if [ "$DB_EXISTS" = "yes" ]; then
    echo -e "${GREEN}✓${NC} 数据库 mac_agent 已存在"
else
    # 尝试不同的连接方式（使用端口 5433）
    if psql -U postgres -p 5433 -c "SELECT 1" &>/dev/null; then
        # 使用 postgres 用户
        psql -U postgres -p 5433 <<EOF
CREATE DATABASE mac_agent;
EOF
        echo -e "${GREEN}✓${NC} 数据库 mac_agent 创建成功（使用 postgres 用户）"
    elif psql -d postgres -p 5433 -c "SELECT 1" &>/dev/null; then
        # 使用当前用户
        psql -d postgres -p 5433 <<EOF
CREATE DATABASE mac_agent;
EOF
        echo -e "${GREEN}✓${NC} 数据库 mac_agent 创建成功（使用当前用户）"
    else
        echo -e "${YELLOW}⚠${NC}  无法自动创建数据库，请手动执行："
        echo ""
        echo "  psql -p 5433 postgres"
        echo "  CREATE DATABASE mac_agent;"
        echo "  \\q"
        echo ""
        read -p "按回车键继续，或 Ctrl+C 取消..."
    fi
fi

# 更新 .env 文件
echo ""
echo -e "${BLUE}更新 .env 文件配置...${NC}"

# 检查 DATABASE_URL 是否已配置
if grep -q "^DATABASE_URL=" .env; then
    echo -e "${YELLOW}⚠${NC}  .env 中已存在 DATABASE_URL，跳过自动配置"
    echo -e "${YELLOW}   如需修改，请手动编辑 .env 文件${NC}"
else
    # 尝试检测 PostgreSQL 连接信息
    # 默认使用端口 5433 以避免与 Cursor 编辑器或其他服务冲突
    # Homebrew 安装的 PostgreSQL 默认用户是当前 macOS 用户名
    CURRENT_USER=$(whoami)
    
    # 尝试连接（Homebrew 默认使用当前用户，无需密码）
    if psql -d postgres -p 5433 -c "SELECT 1" &>/dev/null; then
        # Homebrew 默认配置（使用当前用户，无密码）
        DATABASE_URL="postgresql+asyncpg://${CURRENT_USER}@localhost:5433/mac_agent"
    elif psql -U postgres -p 5433 -c "SELECT 1" &>/dev/null; then
        # Postgres.app 默认配置（使用 postgres 用户）
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/mac_agent"
    else
        # 默认使用当前用户
        DATABASE_URL="postgresql+asyncpg://${CURRENT_USER}@localhost:5433/mac_agent"
    fi
    
    # 添加到 .env 文件
    if ! grep -q "^DATABASE_URL=" .env; then
        echo "" >> .env
        echo "# Database Configuration" >> .env
        echo "DATABASE_URL=${DATABASE_URL}" >> .env
        echo "DB_POOL_SIZE=20" >> .env
        echo "DB_MAX_OVERFLOW=10" >> .env
        echo "DB_ECHO=false" >> .env
        echo -e "${GREEN}✓${NC} DATABASE_URL 已添加到 .env"
    fi
fi

# 运行数据库迁移
echo ""
echo -e "${BLUE}运行数据库迁移...${NC}"
cd backend

if [ ! -d ".venv" ]; then
    echo -e "${RED}错误: 未找到后端虚拟环境${NC}"
    echo -e "${YELLOW}请先运行: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt${NC}"
    exit 1
fi

source .venv/bin/activate

# 检查 alembic 是否已安装
if ! python -c "import alembic" &>/dev/null; then
    echo -e "${YELLOW}安装数据库迁移工具...${NC}"
    pip install alembic asyncpg &>/dev/null
fi

# 运行迁移
if alembic upgrade head &>/dev/null; then
    echo -e "${GREEN}✓${NC} 数据库迁移完成"
else
    echo -e "${YELLOW}⚠${NC}  数据库迁移可能失败，请检查错误信息"
    echo -e "${YELLOW}   手动运行: cd backend && source .venv/bin/activate && alembic upgrade head${NC}"
fi

cd ..

# 完成
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}   ✅ PostgreSQL 设置完成！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "下一步："
echo -e "  1. 检查 .env 文件中的 DATABASE_URL 配置是否正确"
echo -e "  2. 启动服务: ${BLUE}./start_prod.sh${NC}"
echo -e "  3. 验证连接: ${BLUE}curl http://localhost:18888/health/detailed${NC}"
echo ""
echo -e "详细文档: ${BLUE}docs/setup/postgresql_setup_macos.md${NC}"
echo ""
