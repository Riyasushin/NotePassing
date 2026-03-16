#!/bin/bash
# 稳定后台启动后端服务

set -euo pipefail

cd "$(dirname "$0")"

ROOT_DIR="$(pwd)"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
PID_FILE="$ROOT_DIR/.backend.pid"
LOG_FILE="$ROOT_DIR/log"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo "🚀 启动 NotePassing 后端服务..."

if [[ ! -x "$PYTHON_BIN" ]]; then
	echo "❌ 未找到 Python 虚拟环境: $PYTHON_BIN"
	exit 1
fi

if [[ -f "$PID_FILE" ]]; then
	EXISTING_PID="$(cat "$PID_FILE")"
	if [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" 2>/dev/null; then
		echo "✅ 后端已在运行，PID: $EXISTING_PID"
		exit 0
	fi
	rm -f "$PID_FILE"
fi

echo "📦 启动 PostgreSQL 数据库..."
docker compose up -d db

echo "⏳ 等待数据库就绪..."
DB_CONTAINER_ID="$(docker compose ps -q db)"
if [[ -n "$DB_CONTAINER_ID" ]]; then
	for _ in $(seq 1 30); do
		DB_STATUS="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$DB_CONTAINER_ID" 2>/dev/null || true)"
		if [[ "$DB_STATUS" == "healthy" || "$DB_STATUS" == "running" ]]; then
			break
		fi
		sleep 1
	done
fi

echo "🌐 启动 Uvicorn 服务器..."
nohup "$PYTHON_BIN" -m uvicorn app.main:app --host "$HOST" --port "$PORT" >> "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

for _ in $(seq 1 30); do
	if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
		echo "✅ 后端启动成功，PID: $SERVER_PID"
		echo "====================================="
		echo "  API:     http://localhost:$PORT"
		echo "  Docs:    http://localhost:$PORT/docs"
		echo "  Health:  http://localhost:$PORT/health"
		echo "  Log:     $LOG_FILE"
		echo "====================================="
		exit 0
	fi

	if ! kill -0 "$SERVER_PID" 2>/dev/null; then
		echo "❌ 后端进程启动后立即退出，请检查日志: $LOG_FILE"
		rm -f "$PID_FILE"
		exit 1
	fi

	sleep 1
done

echo "❌ 后端健康检查超时，请检查日志: $LOG_FILE"
kill "$SERVER_PID" 2>/dev/null || true
rm -f "$PID_FILE"
exit 1
