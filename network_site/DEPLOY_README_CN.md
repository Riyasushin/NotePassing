# NotePassing Network Site ɵ�ϲ���˵��

����ĵ����򡰲��� Web �������Ĳ���ʽ��

Ŀ��Ч����

- ������ҳ��Ȼʹ�� `http://39.105.30.179:8000/`
- ��ҳ��ʾ����ͼ��վ
- ԭ���� NotePassing ��� API ��������
- ���޸�ԭ��Ŀ�ṹ��ֻ����������վ��Ŀ��ͨ�� Nginx ת��

## ���ǰ��

Ĭ����ķ���������ĿĿ¼�ǣ�

```bash
/root/NotePassing
```

并且目录里已经有：

```bash
/root/NotePassing/backend
/root/NotePassing/network_site
```

如果你的项目不在这个目录，把下面脚本里的：

```bash
PROJECT_DIR="/root/NotePassing"
```

改成你自己的实际路径。

## 一键部署

SSH 登录你的 Linux 服务器后，直接复制下面整段执行：

```bash
sudo bash <<'BASH'
set -e

PROJECT_DIR="/root/NotePassing"
SERVER_IP="39.102.97.149"

if [ ! -d "$PROJECT_DIR/backend" ] || [ ! -d "$PROJECT_DIR/network_site" ]; then
  echo "项目目录不对。请确认这两个目录存在："
  echo "  $PROJECT_DIR/backend"
  echo "  $PROJECT_DIR/network_site"
  exit 1
fi

if [ ! -f "$PROJECT_DIR/backend/.env" ]; then
  echo "缺少 $PROJECT_DIR/backend/.env"
  exit 1
fi

apt-get update
apt-get install -y nginx python3 python3-venv python3-pip psmisc

DB_URL="$(grep '^DATABASE_URL=' "$PROJECT_DIR/backend/.env" | head -n1 | cut -d= -f2-)"
if [ -z "$DB_URL" ]; then
  echo "没有在 $PROJECT_DIR/backend/.env 里找到 DATABASE_URL"
  exit 1
fi

if [ ! -x "$PROJECT_DIR/backend/.venv/bin/python3" ]; then
  python3 -m venv "$PROJECT_DIR/backend/.venv"
fi
"$PROJECT_DIR/backend/.venv/bin/pip" install --upgrade pip
"$PROJECT_DIR/backend/.venv/bin/pip" install -e "$PROJECT_DIR/backend"

if [ ! -x "$PROJECT_DIR/network_site/.venv/bin/python3" ]; then
  python3 -m venv "$PROJECT_DIR/network_site/.venv"
fi
"$PROJECT_DIR/network_site/.venv/bin/pip" install --upgrade pip
"$PROJECT_DIR/network_site/.venv/bin/pip" install -r "$PROJECT_DIR/network_site/requirements.txt"

cat > "$PROJECT_DIR/network_site/.env" <<EOF
NP_SITE_DATABASE_URL=$DB_URL
NP_SITE_REFRESH_SECONDS=5
NP_SITE_PRESENCE_SECONDS=180
NP_SITE_MESSAGE_MINUTES=15
NP_SITE_MAX_NODES=80
EOF

cat > /etc/systemd/system/notepassing-backend.service <<EOF
[Unit]
Description=NotePassing Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR/backend
EnvironmentFile=$PROJECT_DIR/backend/.env
ExecStart=$PROJECT_DIR/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/notepassing-network-site.service <<EOF
[Unit]
Description=NotePassing Network Site
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR/network_site
EnvironmentFile=$PROJECT_DIR/network_site/.env
ExecStart=$PROJECT_DIR/network_site/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8090
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

rm -f /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-available/default

cat > /etc/nginx/conf.d/notepassing.conf <<EOF
server {
    listen 8000;
    server_name $SERVER_IP;

    client_max_body_size 10m;

    location /api/v1/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /redoc {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /uploads/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location = /api-health {
        proxy_pass http://127.0.0.1:8001/health;
        proxy_set_header Host \$host;
    }

    location / {
        proxy_pass http://127.0.0.1:8090;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

nginx -t
systemctl daemon-reload
systemctl enable notepassing-backend.service
systemctl enable notepassing-network-site.service
systemctl enable nginx

fuser -k 8000/tcp || true

systemctl restart notepassing-backend.service
systemctl restart notepassing-network-site.service
systemctl restart nginx

if command -v ufw >/dev/null 2>&1; then
  ufw allow 8000/tcp || true
fi

echo
echo "部署完成。"
echo "主页: http://$SERVER_IP:8000/"
echo "后端健康检查: http://$SERVER_IP:8000/api-health"
echo
systemctl --no-pager --full status notepassing-backend.service | sed -n '1,12p'
echo
systemctl --no-pager --full status notepassing-network-site.service | sed -n '1,12p'
echo
systemctl --no-pager --full status nginx.service | sed -n '1,12p'
BASH
```

## 部署完成后怎么检查

浏览器打开：

```bash
http://39.102.97.149:8000/
```

如果首页能打开，说明网站已启动。

再打开：

```bash
http://39.102.97.149:8000/api-health
```

如果看到健康状态，说明后端也正常。

## 平时重启命令

```bash
sudo systemctl restart notepassing-backend
sudo systemctl restart notepassing-network-site
sudo systemctl restart nginx
```

## 平时查看运行状态

```bash
sudo systemctl status notepassing-backend
sudo systemctl status notepassing-network-site
sudo systemctl status nginx
```

## 查看报错日志

```bash
sudo journalctl -u notepassing-network-site -n 100 --no-pager
sudo journalctl -u notepassing-backend -n 100 --no-pager
```

## 如果部署失败，最常见的原因

### 1. 项目目录不对

如果提示：

```bash
项目目录不对
```

就把脚本里的：

```bash
PROJECT_DIR="/root/NotePassing"
```

改成你服务器上的真实路径。

### 2. 后端 `.env` 不存在

如果提示：

```bash
缺少 /root/NotePassing/backend/.env
```

说明你原后端的环境变量文件还没放好，需要先把它补上。

### 3. 数据库连接串没找到

如果提示：

```bash
没有在 backend/.env 里找到 DATABASE_URL
```

说明你需要在：

```bash
/root/NotePassing/backend/.env
```

里加上：

```bash
DATABASE_URL=你的数据库连接串
```

### 4. 8000 端口被别的程序占用

脚本里已经会自动尝试释放 `8000`，但如果还有问题，可以执行：

```bash
sudo fuser -k 8000/tcp
sudo systemctl restart nginx
```

## 文件位置

这份部署文档文件在：

[DEPLOY_README_CN.md](/D:/User/projects/NotePassing/network_site/DEPLOY_README_CN.md)
