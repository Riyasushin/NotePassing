#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")"

ROOT_DIR="$(pwd)"
BACKEND_DIR="$(cd "$ROOT_DIR/../backend" && pwd)"
PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"
ENV_FILE="$BACKEND_DIR/.env"
PID_FILE="$ROOT_DIR/.network_site.pid"
LOG_FILE="$ROOT_DIR/site.log"

echo "🚀 启动 Network Site..."

if [[ ! -x "$PYTHON_BIN" ]]; then
	echo "❌ 未找到 Python 虚拟环境: $PYTHON_BIN"
	exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
	echo "❌ 未找到环境文件: $ENV_FILE"
	exit 1
fi

if [[ -f "$PID_FILE" ]]; then
	EXISTING_PID="$(cat "$PID_FILE")"
	if [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" 2>/dev/null; then
		echo "✅ 网站已在运行，PID: $EXISTING_PID"
		exit 0
	fi
	rm -f "$PID_FILE"
fi

while IFS= read -r line || [[ -n "$line" ]]; do
	[[ -z "$line" || "$line" == \#* ]] && continue
	[[ "$line" != *=* ]] && continue

	case "$line" in
		DATABASE_URL=*|NP_SITE_*=*) ;;
		*) continue ;;
	esac

	export "$line"
done < "$ENV_FILE"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8090}"

nohup "$PYTHON_BIN" -m uvicorn app:app --host "$HOST" --port "$PORT" >> "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

for _ in $(seq 1 30); do
	if curl -fsS "http://127.0.0.1:$PORT/" >/dev/null 2>&1; then
		echo "✅ 网站启动成功，PID: $SERVER_PID"
		echo "====================================="
		echo "  URL:     http://localhost:$PORT"
		echo "  Log:     $LOG_FILE"
		echo "====================================="
		exit 0
	fi

	if ! kill -0 "$SERVER_PID" 2>/dev/null; then
		echo "❌ 网站进程启动后立即退出，请检查日志: $LOG_FILE"
		rm -f "$PID_FILE"
		exit 1
	fi

	sleep 1
done

echo "❌ 网站健康检查超时，请检查日志: $LOG_FILE"
kill "$SERVER_PID" 2>/dev/null || true
rm -f "$PID_FILE"
exit 1
