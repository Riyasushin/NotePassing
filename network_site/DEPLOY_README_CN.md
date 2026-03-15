# NotePassing Network Site ɵ�ϲ���˵��

����ĵ����򡰲��� Web �������Ĳ���ʽ��

Ŀ��Ч����

- ������ҳ��Ȼʹ�� `http://39.102.97.149:8000/`
- ��ҳ��ʾ����ͼ��վ
- ԭ���� NotePassing ��� API ��������
- ���޸�ԭ��Ŀ�ṹ��ֻ����������վ��Ŀ��ͨ�� Nginx ת��

## ���ǰ��

Ĭ����ķ���������ĿĿ¼�ǣ�

```bash
/root/NotePassing
```

����Ŀ¼���Ѿ��У�

```bash
/root/NotePassing/backend
/root/NotePassing/network_site
```

��������Ŀ�������Ŀ¼��������ű���ģ�

```bash
PROJECT_DIR="/root/NotePassing"
```

�ĳ����Լ���ʵ��·����

## һ������

SSH ��¼��� Linux ��������ֱ�Ӹ�����������ִ�У�

```bash
sudo bash <<'BASH'
set -e

PROJECT_DIR="/root/NotePassing"
SERVER_IP="39.102.97.149"

if [ ! -d "$PROJECT_DIR/backend" ] || [ ! -d "$PROJECT_DIR/network_site" ]; then
  echo "��ĿĿ¼���ԡ���ȷ��������Ŀ¼���ڣ�"
  echo "  $PROJECT_DIR/backend"
  echo "  $PROJECT_DIR/network_site"
  exit 1
fi

if [ ! -f "$PROJECT_DIR/backend/.env" ]; then
  echo "ȱ�� $PROJECT_DIR/backend/.env"
  exit 1
fi

apt-get update
apt-get install -y nginx python3 python3-venv python3-pip psmisc

DB_URL="$(grep '^DATABASE_URL=' "$PROJECT_DIR/backend/.env" | head -n1 | cut -d= -f2-)"
if [ -z "$DB_URL" ]; then
  echo "û���� $PROJECT_DIR/backend/.env ���ҵ� DATABASE_URL"
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
echo "������ɡ�"
echo "��ҳ: http://$SERVER_IP:8000/"
echo "��˽������: http://$SERVER_IP:8000/api-health"
echo
systemctl --no-pager --full status notepassing-backend.service | sed -n '1,12p'
echo
systemctl --no-pager --full status notepassing-network-site.service | sed -n '1,12p'
echo
systemctl --no-pager --full status nginx.service | sed -n '1,12p'
BASH
```

## ������ɺ���ô���

������򿪣�

```bash
http://39.102.97.149:8000/
```

�����ҳ�ܴ򿪣�˵����վ��������

�ٴ򿪣�

```bash
http://39.102.97.149:8000/api-health
```

�����������״̬��˵�����Ҳ������

## ƽʱ��������

```bash
sudo systemctl restart notepassing-backend
sudo systemctl restart notepassing-network-site
sudo systemctl restart nginx
```

## ƽʱ�鿴����״̬

```bash
sudo systemctl status notepassing-backend
sudo systemctl status notepassing-network-site
sudo systemctl status nginx
```

## �鿴������־

```bash
sudo journalctl -u notepassing-network-site -n 100 --no-pager
sudo journalctl -u notepassing-backend -n 100 --no-pager
```

## �������ʧ�ܣ������ԭ��

### 1. ��ĿĿ¼����

�����ʾ��

```bash
��ĿĿ¼����
```

�Ͱѽű���ģ�

```bash
PROJECT_DIR="/root/NotePassing"
```

�ĳ���������ϵ���ʵ·����

### 2. ��� `.env` ������

�����ʾ��

```bash
ȱ�� /root/NotePassing/backend/.env
```

˵����ԭ��˵Ļ��������ļ���û�źã���Ҫ�Ȱ������ϡ�

### 3. ���ݿ����Ӵ�û�ҵ�

�����ʾ��

```bash
û���� backend/.env ���ҵ� DATABASE_URL
```

˵������Ҫ�ڣ�

```bash
/root/NotePassing/backend/.env
```

����ϣ�

```bash
DATABASE_URL=������ݿ����Ӵ�
```

### 4. 8000 �˿ڱ���ĳ���ռ��

�ű����Ѿ����Զ������ͷ� `8000`��������������⣬����ִ�У�

```bash
sudo fuser -k 8000/tcp
sudo systemctl restart nginx
```

## �ļ�λ��

��ݲ����ĵ��ļ��ڣ�

[DEPLOY_README_CN.md](/D:/User/projects/NotePassing/network_site/DEPLOY_README_CN.md)
