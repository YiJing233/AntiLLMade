# AntiLLMade Microservices

微服务化后的 AntiLLMade 架构。

## 服务列表

| 服务 | 端口 | 职责 |
|------|------|------|
| gateway | 8000 | API 网关 (路由/限流/认证) |
| summary-service | 8001 | AI 摘要生成 |
| source-service | 8002 | 订阅源管理 |
| rss-service | 8003 | RSS 拉取和解析 |
| digest-service | 8004 | 日报聚合 |
| data-service | 8005 | 数据持久化 (PostgreSQL) |
| scheduler | 8006 | 定时调度 |
| mcp-tools | 8007 | MCP 工具接口 |
| frontend | 5173 | 前端 UI |
| redis | 6379 | 缓存/消息队列 |
| postgres | 5432 | 主数据库 |

## 快速启动

```bash
cd playground/AntiLLMade

# 启动所有服务
docker compose -f docker-compose.split.yml up -d

# 查看日志
docker compose -f docker-compose.split.yml logs -f

# 停止所有服务
docker compose -f docker-compose.split.yml down
```

## 各服务独立启动

```bash
# 启动 Redis
docker compose -f docker-compose.split.yml up -d redis

# 启动 PostgreSQL
docker compose -f docker-compose.split.yml up -d postgres

# 启动各服务 (按依赖顺序)
docker compose -f docker-compose.split.yml up -d summary-service
docker compose -f docker-compose.split.yml up -d source-service
docker compose -f docker-compose.split.yml up -d rss-service
docker compose -f docker-compose.split.yml up -d digest-service
docker compose -f docker-compose.split.yml up -d data-service
docker compose -f docker-compose.split.yml up -d gateway
docker compose -f docker-compose.split.yml up -d scheduler
docker compose -f docker-compose.split.yml up -d mcp-tools
docker compose -f docker-compose.split.yml up -d frontend
```

## 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│   Gateway   │────▶│    ...      │
│  (5173)     │     │   (8000)    │     │  services   │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
  │   Summary   │   │    RSS      │   │   Digest    │
  │ (8001)      │   │ (8003)      │   │ (8004)      │
  └─────────────┘   └──────┬──────┘   └─────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
             ┌───────────┐  ┌───────────┐
             │   Data    │  │  Redis   │
             │ (8005)    │  │  (6379)  │
             └───────────┘  └───────────┘
```

## 环境变量

```bash
# AI 配置
export OPENAI_API_KEY="your-key"
export OPENAI_MODEL="gpt-4o-mini"

# 数据库
export DATABASE_URL="postgresql://user:pass@localhost:5432/antillmade"

# OpenClaw
export OPENCLAW_WEBHOOK="https://your-hook"
```

## 健康检查

```bash
# 检查所有服务状态
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
# ...
```
