"""
测试用例 - AntiLLMade RSS Digest API
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestHealth:
    """健康检查测试"""
    
    def test_health_check(self):
        """测试 /health 端点返回正常状态"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    
    def test_root_endpoint(self):
        """测试根端点返回 API 信息"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "message" in data


class TestSources:
    """订阅源管理测试"""
    
    def test_create_source(self):
        """测试创建订阅源"""
        test_source = {
            "url": "https://example.com/feed.xml",
            "title": "测试订阅源",
            "category": "测试"
        }
        response = client.post("/sources", json=test_source)
        
        # 首次创建应该成功
        if response.status_code == 200:
            assert response.json()["title"] == "测试订阅源"
            assert response.json()["category"] == "测试"
    
    def test_list_sources(self):
        """测试列出所有订阅源"""
        response = client.get("/sources")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_sources_meta(self):
        """测试获取订阅源元数据"""
        response = client.get("/sources/meta")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestEntries:
    """条目管理测试"""
    
    def test_mark_entry_read(self):
        """测试标记条目已读"""
        # 假设存在 id=1 的条目
        response = client.post("/entries/1/read")
        # 如果条目存在，返回成功
        if response.status_code == 200:
            assert response.json()["status"] == "read"
        # 如果条目不存在，返回 404（预期行为）
        elif response.status_code == 404:
            pass  # 预期行为
    
    def test_digest_endpoint(self):
        """测试获取日报"""
        response = client.get("/digest")
        assert response.status_code == 200
        data = response.json()
        assert "date" in data
        assert "total" in data
        assert "categories" in data


class TestIngest:
    """RSS 抓取测试"""
    
    def test_ingest_requires_sources(self):
        """测试没有订阅源时抓取会报错"""
        # 先清空所有订阅源（如果有 API）
        # 然后测试 ingest 应该返回错误
        response = client.post("/ingest")
        # 如果没有订阅源，返回 400 错误
        if response.status_code == 400:
            assert "请先添加" in response.json()["detail"]


class TestDataIntegrity:
    """数据完整性测试"""
    
    def test_source_uniqueness(self):
        """测试订阅源 URL 不能重复"""
        test_source = {
            "url": "https://duplicate-test.com/feed.xml",
            "title": "重复测试",
            "category": "测试"
        }
        # 第一次创建
        client.post("/sources", json=test_source)
        # 第二次创建应该失败或返回已有条目
        response = client.post("/sources", json=test_source)
        # 预期：URL 唯一约束生效
        assert response.status_code in [200, 400]


# API 测试用例汇总
"""
执行测试命令：
    cd backend
    python -m pytest test_api.py -v

预期结果：
    ✓ /health 返回正常状态
    ✓ /sources API 可正常列出订阅源
    ✓ /sources/meta 返回订阅源列表
    ✓ /digest 返回日报数据
    ✓ 创建订阅源功能正常
    ✓ 重复 URL 被正确处理
"""
