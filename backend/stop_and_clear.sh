#!/bin/bash
# 停止服务并清空数据库数据

set -e

echo "🛑 正在停止服务..."

# 停止 uvicorn 服务器
pkill -f "uvicorn app.main:app" 2>/dev/null || echo "  Uvicorn 未运行"

# 停止 Docker 容器并删除数据卷
echo "🗑️  正在停止数据库并清空数据..."
docker compose down -v

echo "✅ 服务已停止，数据库数据已清空"
