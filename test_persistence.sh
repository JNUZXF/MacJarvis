#!/bin/bash
# File: test_persistence.sh
# Purpose: 测试聊天记录持久化功能

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  聊天记录持久化功能测试${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 1. 测试机器ID生成
echo -e "${YELLOW}[1/5] 测试机器ID生成...${NC}"
cd backend
source .venv/bin/activate
MACHINE_ID=$(python -c "from app.core.machine_id import get_machine_id; print(get_machine_id())" 2>/dev/null | tail -1)
echo -e "${GREEN}✓${NC} 机器ID: ${MACHINE_ID:0:16}..."
echo ""

# 2. 验证缓存文件
echo -e "${YELLOW}[2/5] 验证缓存文件...${NC}"
if [ -f ~/.mac_agent/machine_id ]; then
    CACHED_ID=$(cat ~/.mac_agent/machine_id)
    if [ "$MACHINE_ID" = "$CACHED_ID" ]; then
        echo -e "${GREEN}✓${NC} 缓存文件存在且内容正确"
        ls -lh ~/.mac_agent/machine_id
    else
        echo -e "${YELLOW}⚠${NC} 缓存文件内容不匹配"
    fi
else
    echo -e "${YELLOW}⚠${NC} 缓存文件不存在"
fi
echo ""

# 3. 验证数据库路径
echo -e "${YELLOW}[3/5] 验证数据库配置...${NC}"
DB_PATH=$(python -c "from app.config import get_settings; s = get_settings(); print(s.effective_database_url)" 2>/dev/null | tail -1)
echo -e "${GREEN}✓${NC} 数据库URL: ${DB_PATH}"
echo ""

# 4. 运行单元测试
echo -e "${YELLOW}[4/5] 运行单元测试...${NC}"
pytest tests/test_machine_id.py -v --tb=short -q
echo ""

# 5. 显示数据目录
echo -e "${YELLOW}[5/5] 数据目录结构...${NC}"
if [ -d ~/.mac_agent ]; then
    echo -e "${GREEN}✓${NC} 数据目录: ~/.mac_agent/"
    tree -L 2 ~/.mac_agent/ 2>/dev/null || ls -lhR ~/.mac_agent/
else
    echo -e "${YELLOW}⚠${NC} 数据目录不存在"
fi
echo ""

# 总结
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}  ✅ 测试完成！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "数据存储位置："
echo -e "  - 机器ID缓存: ${BLUE}~/.mac_agent/machine_id${NC}"
echo -e "  - 数据库文件: ${BLUE}~/.mac_agent/data/app.db${NC}"
echo -e "  - 上传文件: ${BLUE}~/.mac_agent/uploads/${NC}"
echo ""
echo -e "使用说明："
echo -e "  1. 启动项目: ${BLUE}./start_prod.sh${NC}"
echo -e "  2. 访问前端: ${BLUE}http://localhost:18889${NC}"
echo -e "  3. 聊天记录将自动保存到 ~/.mac_agent/data/app.db"
echo -e "  4. 重启系统或更换浏览器后，历史记录依然存在"
echo ""
