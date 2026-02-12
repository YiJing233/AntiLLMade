# Vercel 部署指南

AntiLLMade 是一个前后端分离的应用，推荐的部署架构：

## 📐 架构

```
┌─────────────────────────────────────────────────────┐
│                   Vercel (Frontend)                │
│  ┌─────────────────────────────────────────────┐  │
│  │  React + Vite (静态站点)                     │  │
│  │  - 域名: https://your-project.vercel.app     │  │
│  │  - API 代理到后端                            │  │
│  └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│              Railway/Render (Backend)               │
│  ┌─────────────────────────────────────────────┐  │
│  │  FastAPI + SQLite                          │  │
│  │  - 域名: https://your-api.railway.app     │  │
│  │  - RSS 抓取、摘要生成、日报 API             │  │
│  └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## 🚀 部署步骤

### 1. 部署后端 (Railway/Render)

**推荐: Railway**

1. 访问 https://railway.app
2. "New Project" → "Deploy from GitHub"
3. 选择 `YiJing233/AntiLLMade` 仓库
4. 配置：
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. 设置环境变量：
   ```
   OPENAI_API_KEY=your_key_here  # 可选
   ```
6. 部署完成后获取 API 地址: `https://your-app.railway.app`

**或者: Render**

1. 访问 https://render.com
2. "New Web Service"
3. 同样配置 Root Directory 为 `backend`

---

### 2. 部署前端 (Vercel)

**方式一: Vercel CLI**

```bash
# 安装 Vercel CLI
npm i -g vercel

# 登录
vercel login

# 部署
cd /path/to/AntiLLMade
vercel
```

**方式二: Vercel Dashboard**

1. 访问 https://vercel.com
2. "Add New Project" → "Import Git Repository"
3. 选择 `YiJing233/AntiLLMade`
4. 配置：
   - **Framework Preset**: Vite
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Output Directory**: `frontend/dist`
5. 添加环境变量：
   ```
   VITE_API_BASE=https://your-api.railway.app
   ```
6. Deploy

---

### 3. 配置跨域 (CORS)

确保后端允许 Vercel 前端访问：

```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.vercel.app"],
    allow_credentials=True,
)
```

---

### 4. 配置定时任务

定时抓取需要在后端服务器上配置：

**Railway:**
1. Railway Dashboard → Your Service → "Jobs" (或使用 Cron)
2. 设置 cron: `0 4 * * *` (UTC 每天4点 = 北京时间12点)

**或者: GitHub Actions**

```yaml
# .github/workflows/rss-ingest.yml
name: Daily RSS Ingest

on:
  schedule:
    - cron: '0 4 * * *'  # UTC 4:00 = 北京时间 12 workflow_dispatch:

jobs:
  ingest:00
 :
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Ingest
        run: |
          curl -X POST "https://your-api.railway.app/ingest"
```

---

## 🔧 配置说明

### 环境变量

**前端 (.env.production):**
```
VITE_API_BASE=https://your-backend-api.com
```

**后端 (Railway/Render):**
```
OPENAI_API_KEY=sk-xxx  # 可选，用于 AI 摘要生成
```

---

## 📁 目录结构

```
AntiLLMade/
├── frontend/          # React 前端 (Vercel)
├── backend/           # FastAPI 后端 (Railway/Render)
├── agents/           # Agent 配置
├── automation/      # 自动化脚本
├── data/             # 数据文件
├── vercel.json       # Vercel 配置 ✓
└── README.md
```

---

## ✅ 验证部署

1. **前端**: 访问 `https://your-project.vercel.app`
2. **后端健康检查**: `https://your-api.railway.app/health`
3. **API 文档**: `https://your-api.railway.app/docs`

---

## 🆘 常见问题

### Q: Vercel 部署后 API失败
 请求A: 检查 `vercel.json` 中的 `VITE_API_BASE` 环境变量配置

### Q: 后端跨域错误
A: 在 `backend/main.py` 中添加 CORS 配置

### Q: RSS 抓取失败
A: 检查后端日志，确保网络连接正常

---

## 🎯 推荐方案总结

| 组件 | 平台 | 成本 |
|------|------|------|
| 前端 | Vercel | 免费 |
| 后端 | Railway | 免费额度 |
| 数据库 | SQLite (文件) | 免费 |
| 定时任务 | Railway Cron / GitHub Actions | 免费 |
