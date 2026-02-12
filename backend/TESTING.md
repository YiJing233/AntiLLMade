# 测试指南

AntiLLMade 提供了两种测试方式：自动测试和手动测试。

## 🧪 测试方式

### 1. 手动测试（推荐用于调试）

```bash
cd backend
python3 test_manual.py
```

输出示例：
```
============================================================
  健康检查测试
============================================================
  ✅ GET /health
     响应: {'status': 'ok'}
```

### 2. pytest 自动化测试

```bash
cd backend
pip install pytest httpx
pytest test_api.py -v
```

---

## 📋 测试用例列表

### 健康检查
- ✅ `/health` - 服务健康状态
- ✅ `/` - 根端点信息

### 订阅源管理
- ✅ 创建订阅源 (POST /sources)
- ✅ 列出订阅源 (GET /sources)
- ✅ 获取元数据 (GET /sources/meta)
- ✅ 删除订阅源 (DELETE /sources/{id})
- ✅ URL 唯一性约束

### 内容管理
- ✅ 获取日报 (GET /digest)
- ✅ 标记已读 (POST /entries/{id}/read)
- ✅ RSS 抓取 (POST /ingest)

---

## 🔧 CI/CD 测试命令

```bash
# 安装依赖
pip install -r requirements.txt
pip install pytest httpx

# 运行测试
pytest test_api.py -v --tb=short
```

---

## ✅ 预期测试结果

```
test_api.py::TestHealth::test_health_check PASSED
test_api.py::TestHealth::test_root_endpoint PASSED
test_api.py::TestSources::test_create_source PASSED
test_api.py::TestSources::test_list_sources PASSED
test_api.py::TestSources::test_sources_meta PASSED
test_api.py::TestEntries::test_mark_entry_read PASSED
test_api.py::TestEntries::test_digest_endpoint PASSED
test_api.py::TestDataIntegrity::test_source_uniqueness PASSED

=================== 8 passed in 2.31s ===================
```
