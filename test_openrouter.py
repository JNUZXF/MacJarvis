"""
文件功能: OpenRouter API性能测试脚本 - 分析网络请求延迟
文件路径: /Users/xinfuzhang/Desktop/Code/mac_agent/test_openrouter.py
"""

from openai import OpenAI
import os
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

# 配置代理
PROXY_URL = "http://127.0.0.1:7897"

print("=" * 80)
print("OpenRouter API 性能测试 - 网络请求延迟分析")
print("=" * 80)

# 测试1: 不使用代理的情况
print("\n【测试1: 直连OpenRouter (不使用代理)】")
print("-" * 80)

start_time = time.time()
client_direct = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

model = "bytedance-seed/seed-1.6"

request_start = time.time()
response_direct = client_direct.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "你能做啥"}],
    extra_body={"reasoning": {"enabled": False}},
    stream=True
)

first_token_time = None
token_count = 0
content_parts = []

for chunk in response_direct:
    if first_token_time is None:
        first_token_time = time.time()
        ttft = first_token_time - request_start  # Time To First Token
        print(f"✓ 首token耗时 (TTFT): {ttft:.3f}秒")
    
    if chunk.choices and chunk.choices[0].delta.content:
        token_count += 1
        content_parts.append(chunk.choices[0].delta.content)

total_time = time.time() - request_start
print(f"✓ 总耗时: {total_time:.3f}秒")
print(f"✓ 接收token数: {token_count}")
print(f"✓ 响应内容: {''.join(content_parts)[:100]}...")

# 测试2: 使用代理的情况
print("\n【测试2: 通过Clash代理连接OpenRouter】")
print(f"代理地址: {PROXY_URL}")
print("-" * 80)

start_time = time.time()

# 创建自定义的httpx客户端,配置代理
http_client = httpx.Client(
    proxy=PROXY_URL,
    timeout=60.0,
)

client_proxy = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    http_client=http_client,
)

request_start = time.time()
response_proxy = client_proxy.chat.completions.create(
    model="google/gemini-2.5-flash",
    messages=[{"role": "user", "content": "你能做啥"}],
    extra_body={"reasoning": {"enabled": False}},
    stream=True
)

first_token_time = None
token_count = 0
content_parts = []

for chunk in response_proxy:
    if first_token_time is None:
        first_token_time = time.time()
        ttft = first_token_time - request_start
        print(f"✓ 首token耗时 (TTFT): {ttft:.3f}秒")
    
    if chunk.choices and chunk.choices[0].delta.content:
        token_count += 1
        content_parts.append(chunk.choices[0].delta.content)

total_time = time.time() - request_start
print(f"✓ 总耗时: {total_time:.3f}秒")
print(f"✓ 接收token数: {token_count}")
print(f"✓ 响应内容: {''.join(content_parts)[:100]}...")

# 测试3: 详细的网络层面分析
print("\n【测试3: 详细网络层面分析】")
print("-" * 80)

import socket
import ssl

def test_dns_resolution():
    """测试DNS解析时间"""
    start = time.time()
    try:
        ip = socket.gethostbyname("openrouter.ai")
        elapsed = time.time() - start
        print(f"✓ DNS解析: {elapsed:.3f}秒 -> IP: {ip}")
        return elapsed
    except Exception as e:
        print(f"✗ DNS解析失败: {e}")
        return None

def test_tcp_connection(host, port=443):
    """测试TCP连接时间"""
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        elapsed = time.time() - start
        print(f"✓ TCP连接: {elapsed:.3f}秒")
        sock.close()
        return elapsed
    except Exception as e:
        print(f"✗ TCP连接失败: {e}")
        return None

def test_tls_handshake(host, port=443):
    """测试TLS握手时间"""
    start = time.time()
    try:
        context = ssl.create_default_context()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        
        tls_start = time.time()
        with context.wrap_socket(sock, server_hostname=host) as ssock:
            elapsed = time.time() - tls_start
            print(f"✓ TLS握手: {elapsed:.3f}秒")
            print(f"  TLS版本: {ssock.version()}")
        return elapsed
    except Exception as e:
        print(f"✗ TLS握手失败: {e}")
        return None

def test_proxy_connection():
    """测试代理连接"""
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect(("127.0.0.1", 7897))
        elapsed = time.time() - start
        print(f"✓ 代理连接 (127.0.0.1:7897): {elapsed:.3f}秒")
        sock.close()
        return elapsed
    except Exception as e:
        print(f"✗ 代理连接失败: {e}")
        return None

print("\n直连测试:")
dns_time = test_dns_resolution()
tcp_time = test_tcp_connection("openrouter.ai")
tls_time = test_tls_handshake("openrouter.ai")

print("\n代理测试:")
proxy_conn_time = test_proxy_connection()

print("\n" + "=" * 80)
print("分析建议:")
print("=" * 80)
print("1. 如果首token耗时(TTFT)过高(>2秒),可能原因:")
print("   - DNS解析慢: 考虑使用8.8.8.8或1.1.1.1等公共DNS")
print("   - TCP连接慢: 网络质量问题,检查网络延迟")
print("   - TLS握手慢: SSL证书验证或加密协商耗时")
print("   - 代理转发慢: Clash代理配置问题或代理节点质量差")
print("   - OpenRouter服务端处理慢: 模型加载或排队")
print("\n2. 如果直连比代理快很多:")
print("   - 检查Clash代理节点质量")
print("   - 尝试更换代理节点")
print("   - 检查Clash规则是否正确匹配openrouter.ai")
print("\n3. 如果两者都慢:")
print("   - 可能是OpenRouter服务端问题")
print("   - 检查是否有网络限制或防火墙")
print("=" * 80)

