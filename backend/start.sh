#!/bin/bash
# 从零开始启动服务

set -e

cd "$(dirname "$0")"

echo "🚀 启动 NotePassing 后端服务..."

# 1. 启动数据库
echo "📦 启动 PostgreSQL 数据库..."
docker compose up -d db

# 2. 等待数据库就绪
echo "⏳ 等待数据库就绪..."
sleep 5

# 3. 运行数据库迁移
echo "🔄 运行数据库迁移..."
uv run alembic upgrade head

# 4. 启动服务器
echo "🌐 启动 Uvicorn 服务器..."
echo ""
echo "====================================="
echo "  API:     http://localhost:8000"
echo "  Docs:    http://localhost:8000/docs"
echo "  Health:  http://localhost:8000/health"
echo "====================================="
echo ""

uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | tee log
