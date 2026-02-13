#!/bin/bash
# 启动所有微服务

set -e

echo "🚀 启动 AntiLLMade 微服务集群..."

# 1. 启动基础设施
echo "📦 启动 Redis..."
docker compose -f docker-compose.split.yml up -d redis

# 2. 启动原子服务
echo "🔧 启动 Summary Service..."
docker compose -f docker-compose.split.yml up -d summary-service

echo "📋 启动 Source Service..."
docker compose -f docker-compose.split.yml up -d source-service

# 3. 启动 monolith (向后兼容)
echo "🏠 启动 Backend..."
docker compose -f docker-compose.split.yml up -d backend

echo "🌐 启动 Frontend..."
docker compose -f docker-compose.split.yml up -d frontend

echo ""
echo "✅ 服务启动完成！"
echo ""
echo "服务地址:"
echo "  - Frontend:   http://localhost:5173"
echo "  - Backend:    http://localhost:8000"
echo "  - Summary:    http://localhost:8001"
echo "  - Source:     http://localhost:8002"
echo "  - Redis:      localhost:6379"
