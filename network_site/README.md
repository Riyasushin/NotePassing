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

1. 进入项目目录
2. 设置数据库连接
3. 启动站点

```bash
cd network_site
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/notepassing"
uvicorn app:app --host 0.0.0.0 --port 8090
```

如果你想单独给这个站点使用变量，也可以设置 `NP_SITE_DATABASE_URL`。

```bash
export NP_SITE_DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/notepassing"
uvicorn app:app --host 0.0.0.0 --port 8090
```

SQLite 示例：

```bash
export DATABASE_URL="sqlite+aiosqlite:///absolute/path/to/test.db"
uvicorn app:app --host 0.0.0.0 --port 8090
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

- `NP_SITE_DATABASE_URL`：优先使用的数据库连接串
- `DATABASE_URL`：如果未设置上面这个，则回退使用它
- `NP_SITE_REFRESH_SECONDS`：前端轮询秒数，默认 `5`
- `NP_SITE_PRESENCE_SECONDS`：蓝牙活跃窗口秒数，默认 `180`
- `NP_SITE_MESSAGE_MINUTES`：消息活跃窗口分钟数，默认 `15`
- `NP_SITE_MAX_NODES`：图中最多保留多少节点，默认 `80`

