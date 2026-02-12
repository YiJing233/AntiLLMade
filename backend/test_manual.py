#!/usr/bin/env python3
"""
RSS Digest API 手动测试脚本

使用方法：
    python3 test_manual.py
"""

import httpx
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(name, success, message=""):
    status = "✅" if success else "❌"
    print(f"  {status} {name}")
    if message and not success:
        print(f"     错误: {message}")


def test_health():
    """测试健康检查"""
    print_header("健康检查测试")
    
    try:
        r = httpx.get(f"{BASE_URL}/health")
        print_result("GET /health", r.status_code == 200, r.text)
        print(f"     响应: {r.json()}")
    except Exception as e:
        print_result("GET /health", False, str(e))


def test_root():
    """测试根端点"""
    print_header("根端点测试")
    
    try:
        r = httpx.get(f"{BASE_URL}/")
        print_result("GET /", r.status_code == 200)
        print(f"     响应: {r.json()}")
    except Exception as e:
        print_result("GET /", False, str(e))


def test_sources_crud():
    """测试订阅源 CRUD"""
    print_header("订阅源 CRUD 测试")
    
    # 1. 创建订阅源
    test_source = {
        "url": f"https://test-{int(time.time())}.com/feed.xml",
        "title": "测试订阅源",
        "category": "测试"
    }
    
    try:
        r = httpx.post(f"{BASE_URL}/sources", json=test_source)
        print_result("创建订阅源", r.status_code == 200)
        if r.status_code == 200:
            source_id = r.json()["id"]
            print(f"     创建的 ID: {source_id}")
        else:
            print(f"     响应: {r.text}")
    except Exception as e:
        print_result("创建订阅源", False, str(e))
    
    # 2. 列出订阅源
    try:
        r = httpx.get(f"{BASE_URL}/sources")
        print_result("列出订阅源", r.status_code == 200)
        sources = r.json()
        print(f"     订阅源数量: {len(sources)}")
    except Exception as e:
        print_result("列出订阅源", False, str(e))
    
    # 3. 获取元数据
    try:
        r = httpx.get(f"{BASE_URL}/sources/meta")
        print_result("获取元数据", r.status_code == 200)
        print(f"     元数据数量: {len(r.json())}")
    except Exception as e:
        print_result("获取元数据", False, str(e))


def test_digest():
    """测试日报"""
    print_header("日报测试")
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    try:
        r = httpx.get(f"{BASE_URL}/digest", params={"date": today})
        print_result(f"GET /digest?date={today}", r.status_code == 200)
        data = r.json()
        print(f"     日期: {data.get('date')}")
        print(f"     总条目: {data.get('total')}")
        print(f"     分类数: {len(data.get('categories', {}))}")
    except Exception as e:
        print_result("获取日报", False, str(e))


def test_ingest():
    """测试 RSS 抓取"""
    print_header("RSS 抓取测试")
    
    try:
        r = httpx.post(f"{BASE_URL}/ingest")
        print_result("POST /ingest", r.status_code in [200, 400])
        print(f"     响应: {r.json()}")
    except Exception as e:
        print_result("抓取 RSS", False, str(e))


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🚀"*30)
    print("  AntiLLMade RSS Digest API 测试")
    print("  时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("🚀"*30 + "\n")
    
    tests = [
        ("健康检查", test_health),
        ("根端点", test_root),
        ("订阅源 CRUD", test_sources_crud),
        ("日报功能", test_digest),
        ("RSS 抓取", test_ingest),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ {name} 测试失败: {e}")
            failed += 1
    
    print("\n" + "📊"*30)
    print(f"  测试完成: ✅ 通过 {passed} | ❌ 失败 {failed}")
    print("📊"*30 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
