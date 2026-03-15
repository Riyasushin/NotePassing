cd /root/NotePassing/network_site
export $(grep DATABASE_URL /root/NotePassing/backend/.env | xargs)
uv run uvicorn app:app --host 0.0.0.0 --port 8090
