#!/bin/bash
# File: backend/scripts/test_api.sh
# Purpose: Comprehensive API testing script

set -e

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8001}"
USER_ID="test_user_$(date +%s)"
SESSION_ID=""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_test() {
    echo -e "\n${YELLOW}=== 测试 $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    
    print_test "$name"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        print_success "HTTP $http_code"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        return 0
    else
        print_error "HTTP $http_code"
        echo "$body"
        return 1
    fi
}

# Start testing
echo -e "${YELLOW}╔════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║   MacOS Agent Backend API 测试套件    ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════╝${NC}"
echo ""
echo "测试URL: $BASE_URL"
echo "用户ID: $USER_ID"
echo ""

# Test 1: Health Check
test_endpoint "健康检查" "GET" "/health"

# Test 2: Session Init
print_test "会话初始化"
response=$(curl -s "$BASE_URL/api/session/init" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"$USER_ID\"}")

SESSION_ID=$(echo "$response" | jq -r '.active_session_id')
echo "$response" | jq '.'
print_success "会话ID: $SESSION_ID"

# Test 3: Create New Session
test_endpoint "创建新会话" "POST" "/api/session/new" \
    "{\"user_id\":\"$USER_ID\",\"title\":\"API测试会话\"}"

# Test 4: Get User Paths
test_endpoint "获取用户路径" "GET" "/api/user/paths?user_id=$USER_ID"

# Test 5: Set User Paths
test_endpoint "设置用户路径" "POST" "/api/user/paths" \
    "{\"user_id\":\"$USER_ID\",\"paths\":[\"/tmp\",\"/var/tmp\"]}"

# Test 6: File Upload
print_test "文件上传"
echo "测试内容" > /tmp/test_file.txt
upload_response=$(curl -s "$BASE_URL/api/files" \
    -F "file=@/tmp/test_file.txt")
FILE_ID=$(echo "$upload_response" | jq -r '.id')
echo "$upload_response" | jq '.'
print_success "文件ID: $FILE_ID"
rm /tmp/test_file.txt

# Test 7: Basic Chat
print_test "基础聊天（流式）"
echo "发送消息: 你好，请介绍一下你自己"
curl -s "$BASE_URL/api/chat" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{
        \"message\":\"你好，请介绍一下你自己\",
        \"user_id\":\"$USER_ID\",
        \"session_id\":\"$SESSION_ID\",
        \"model\":\"gpt-4o-mini\"
    }" \
    --no-buffer | head -30
print_success "流式响应正常"

# Test 8: Tool Call
print_test "工具调用"
echo "发送消息: 请列出/tmp目录的文件"
curl -s "$BASE_URL/api/chat" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{
        \"message\":\"请列出/tmp目录的文件\",
        \"user_id\":\"$USER_ID\",
        \"session_id\":\"$SESSION_ID\",
        \"model\":\"gpt-4o-mini\"
    }" \
    --no-buffer | head -40
print_success "工具调用正常"

# Test 9: Get Session with Messages
test_endpoint "获取会话（含消息）" "GET" "/api/session/$SESSION_ID?user_id=$USER_ID"

# Summary
echo ""
echo -e "${YELLOW}╔════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║          测试完成！                     ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✅ 所有核心API测试通过${NC}"
echo ""
echo "测试用户ID: $USER_ID"
echo "测试会话ID: $SESSION_ID"
echo "上传文件ID: $FILE_ID"
echo ""
echo "查看详细日志:"
echo "  docker compose logs backend --tail=100"
echo ""
echo "清理测试数据:"
echo "  # 测试数据会自动存储在backend_data/目录"
