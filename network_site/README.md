# NotePassing Network Site

一个独立的实时可视化网站项目，用于展示 NotePassing 的接入人数、蓝牙邻近关系和好友网络图。

## 特性

- 实时读取 NotePassing 数据库，不依赖修改原后端代码
- 首页展示当前广播人数、近期蓝牙活跃人数、邻近边数量、好友边数量
- 根据 `presences` 和 `friendships` 计算自适应网络图
- 纯静态前端，无打包步骤，部署简单
- 黑 / 绿 / 白主题，适合作为 Linux 服务器 HTTP 主页

## 数据来源

- `devices`：节点基础信息
- `temp_ids`：统计当前仍在广播的设备数量
- `presences`：计算最近蓝牙邻近关系与活跃设备
- `friendships`：叠加已接受的好友边
- `sessions`：补充临时会话活跃数量
- `messages`：估算最近消息活跃时间

## 接入人数定义

由于第三版设计明确说明服务端不维护全局 `is_online` 字段，因此本项目提供两类实时指标：

- 当前广播人数：`temp_ids.expires_at > now()` 的去重设备数
- 近期蓝牙活跃人数：最近窗口内出现在 `presences.last_seen_at` 的去重设备数

默认窗口：

- 蓝牙活跃窗口：180 秒
- 消息活跃窗口：15 分钟

可通过环境变量调整。

## 运行

### 准备工作

确保你有正确的数据库连接串。如果你已经有 NotePassing backend 在运行，可以直接从它的 `.env` 文件读取：

```bash
# 方法 1：手动查看 backend/.env 中的 DATABASE_URL
cat ../backend/.env | grep DATABASE_URL

# 方法 2：直接导出到当前环境
export $(grep DATABASE_URL ../backend/.env | xargs)
```

默认的数据库连接串格式：
```
postgresql+asyncpg://用户名:密码@主机:端口/数据库名
```

**注意**：如果你用 Docker 运行 PostgreSQL，且 backend 也在 Docker 中，需要确认网络访问方式：
- 如果 site 在宿主机运行，数据库在 Docker：把 `localhost` 换成 `127.0.0.1` 或 Docker 容器 IP
- 如果都在 Docker 中：使用 Docker 网络内的主机名（如 `db`）

### 启动站点

```bash
cd network_site

# 设置数据库连接（使用你实际的用户名、密码）
export DATABASE_URL="postgresql+asyncpg://notepassing:notepassing-secret@localhost:5432/notepassing"

# 启动服务
uvicorn app:app --host 0.0.0.0 --port 8090
```

如果你想单独给这个站点使用变量，也可以设置 `NP_SITE_DATABASE_URL`（优先级更高）：

```bash
export NP_SITE_DATABASE_URL="postgresql+asyncpg://notepassing:notepassing-secret@localhost:5432/notepassing"
uvicorn app:app --host 0.0.0.0 --port 8090
```

SQLite 示例（仅用于测试）：

```bash
export DATABASE_URL="sqlite+aiosqlite:///absolute/path/to/test.db"
uvicorn app:app --host 0.0.0.0 --port 8090
```

### 使用 uv 运行（如果你用 uv 管理依赖）

```bash
cd network_site
export $(grep DATABASE_URL ../backend/.env | xargs)
uv run uvicorn app:app --host 0.0.0.0 --port 8090
```

## 反向代理到 HTTP 主页

Nginx 示例：

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `NP_SITE_DATABASE_URL` | 优先使用的数据库连接串 | - |
| `DATABASE_URL` | 如果未设置上面这个，则回退使用它 | - |
| `NP_SITE_REFRESH_SECONDS` | 前端轮询秒数 | `5` |
| `NP_SITE_PRESENCE_SECONDS` | 蓝牙活跃窗口秒数 | `180` |
| `NP_SITE_MESSAGE_MINUTES` | 消息活跃窗口分钟数 | `15` |
| `NP_SITE_MAX_NODES` | 图中最多保留多少节点 | `80` |

## 故障排查

### 错误：`password authentication failed for user "user"`

说明你使用的数据库连接串中的用户名或密码不正确。请检查：
1. 确认 `../backend/.env` 中的 `DATABASE_URL` 是正确的
2. 确认 PostgreSQL 服务正在运行且可访问
3. 如果使用 Docker，确认主机名和端口映射正确

### 错误：`Connection refused`

- 检查 PostgreSQL 是否正在运行
- 检查主机名是否正确（Docker 环境下可能需要使用 `127.0.0.1` 而不是 `localhost`）
- 检查端口是否正确（默认 5432）
