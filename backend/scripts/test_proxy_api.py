"""
文件功能: 测试代理配置API接口
文件路径: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/scripts/test_proxy_api.py
"""

import requests
import json

API_BASE_URL = "http://localhost:8001"
TEST_USER_ID = "test_user_proxy_123"

def test_get_proxy_config():
    """测试获取代理配置"""
    print("\n【测试1: 获取代理配置】")
    print("-" * 60)
    
    url = f"{API_BASE_URL}/api/user/proxy"
    params = {"user_id": TEST_USER_ID}
    
    response = requests.get(url, params=params)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200

def test_set_proxy_config():
    """测试设置代理配置"""
    print("\n【测试2: 设置代理配置】")
    print("-" * 60)
    
    url = f"{API_BASE_URL}/api/user/proxy"
    data = {
        "user_id": TEST_USER_ID,
        "http_proxy": "http://127.0.0.1:7897",
        "https_proxy": "http://127.0.0.1:7897"
    }
    
    response = requests.post(url, json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200

def test_invalid_proxy_format():
    """测试无效的代理格式"""
    print("\n【测试3: 无效的代理格式】")
    print("-" * 60)
    
    url = f"{API_BASE_URL}/api/user/proxy"
    data = {
        "user_id": TEST_USER_ID,
        "http_proxy": "127.0.0.1:7897",  # 缺少协议前缀
        "https_proxy": "http://127.0.0.1:7897"
    }
    
    response = requests.post(url, json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 400

def test_clear_proxy_config():
    """测试清除代理配置"""
    print("\n【测试4: 清除代理配置】")
    print("-" * 60)
    
    url = f"{API_BASE_URL}/api/user/proxy"
    data = {
        "user_id": TEST_USER_ID,
        "http_proxy": None,
        "https_proxy": None
    }
    
    response = requests.post(url, json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200

def test_verify_cleared():
    """验证代理配置已清除"""
    print("\n【测试5: 验证配置已清除】")
    print("-" * 60)
    
    url = f"{API_BASE_URL}/api/user/proxy"
    params = {"user_id": TEST_USER_ID}
    
    response = requests.get(url, params=params)
    print(f"状态码: {response.status_code}")
    data = response.json()
    print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    # 验证代理配置为None
    success = data.get("http_proxy") is None and data.get("https_proxy") is None
    print(f"验证结果: {'✓ 通过' if success else '✗ 失败'}")
    
    return success

def main():
    print("=" * 60)
    print("代理配置API测试")
    print("=" * 60)
    
    tests = [
        ("获取默认代理配置", test_get_proxy_config),
        ("设置代理配置", test_set_proxy_config),
        ("验证无效格式", test_invalid_proxy_format),
        ("清除代理配置", test_clear_proxy_config),
        ("验证配置已清除", test_verify_cleared),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")

if __name__ == "__main__":
    main()
