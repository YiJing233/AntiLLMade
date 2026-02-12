# AntiLLMade - AI RSS Digest

一个基于 AI 理解的 RSS 阅读页面应用，支持配置订阅源、每日按时间与主题分组的长上下文日报，包含摘要与细节，并附带 MCP 服务器与自动化推送配置示例，便于接入 Codex automation 与 OpenClaw。

## 架构概览

- **Backend (FastAPI)**: 订阅源管理、RSS 拉取、摘要生成、日报聚合。
- **Frontend (React + Vite)**: 日报阅读页与订阅源面板。
- **MCP Server**: 提供工具接口给 Codex/Agent。
- **Automation**: Codex automation 定时任务 + OpenClaw webhook 推送脚本。

## 快速启动

### 1) 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2) 前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。

### 3) MCP 服务器

```bash
cd mcp
pip install mcp httpx
python rss_mcp_server.py
```

设置 `RSS_API_BASE` 环境变量可指向其他后端。

## API 关键功能

- `POST /sources` 添加订阅源
- `GET /sources` 查看订阅源
- `GET /sources/meta` 查看订阅源的未读与最新更新时间
- `POST /entries/{id}/read` 标记条目已读
- `POST /ingest` 拉取最新 RSS 并生成摘要
- `GET /digest?date=YYYY-MM-DD` 获取日报

## 自动化推送

- `automation/codex_automation.yaml`: Codex automation 定时任务示例
- `automation/push_openclaw.py`: OpenClaw webhook 推送脚本

使用前设置环境变量：

```bash
export OPENCLAW_WEBHOOK="https://your-openclaw-hook"
export RSS_API_BASE="http://localhost:8000"
```

## 说明

- 摘要优先使用 `OPENAI_API_KEY`，未配置时回退为文本截取。
- 日报按 `category` 进行分组展示。
