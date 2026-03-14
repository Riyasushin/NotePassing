# NotePassing Server 实现计划 (Implementation Plan)

> 基于 Unified API Contract V2 的服务端实现路线图  
> **日期**: 2026-03-14  
> **目标**: MVP 版本交付

---

## 目录

1. [项目结构](#1-项目结构)
2. [技术栈与依赖](#2-技术栈与依赖)
3. [实现阶段](#3-实现阶段)
4. [数据库设计](#4-数据库设计)
5. [API 实现顺序](#5-api-实现顺序)
6. [WebSocket 实现](#6-websocket-实现)
7. [测试策略](#7-测试策略)
8. [部署计划](#8-部署计划)

---

## 1. 项目结构

```
notepassing-server/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理
│   ├── database.py             # 数据库连接
│   ├── models/                 # SQLAlchemy 模型
│   │   ├── __init__.py
│   │   ├── device.py
│   │   ├── temp_id.py
│   │   ├── presence.py
│   │   ├── message.py
│   │   ├── session.py
│   │   ├── friendship.py
│   │   └── block.py
│   ├── schemas/                # Pydantic 模型
│   │   ├── __init__.py
│   │   ├── device.py
│   │   ├── temp_id.py
│   │   ├── presence.py
│   │   ├── message.py
│   │   ├── friendship.py
│   │   └── common.py
│   ├── services/               # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── device_service.py
│   │   ├── temp_id_service.py
│   │   ├── presence_service.py
│   │   ├── messaging_service.py
│   │   ├── relation_service.py
│   │   └── websocket_manager.py
│   ├── routers/                # API 路由
│   │   ├── __init__.py
│   │   ├── device.py
│   │   ├── temp_id.py
│   │   ├── presence.py
│   │   ├── message.py
│   │   ├── friendship.py
│   │   └── websocket.py
│   ├── utils/                  # 工具函数
│   │   ├── __init__.py
│   │   ├── validators.py
│   │   ├── temp_id_generator.py
│   │   └── rssi_converter.py
│   └── exceptions.py           # 自定义异常
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # pytest 配置
│   ├── unit/                   # 单元测试
│   ├── integration/            # 集成测试
│   └── e2e/                    # 端到端测试
├── alembic/                    # 数据库迁移
│   ├── versions/
│   └── env.py
├── scripts/
│   └── init_db.py              # 数据库初始化脚本
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
└── README.md
```

---

## 2. 技术栈与依赖

### 2.1 核心依赖

```txt
# requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
asyncpg==0.29.0
alembic==1.13.1
redis==5.0.1
pydantic==2.5.3
pydantic-settings==2.1.0
python-multipart==0.0.6
websockets==12.0
```

### 2.2 开发依赖

```txt
# requirements-dev.txt
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-postgresql==5.0.0
httpx==0.26.0
black==24.1.1
isort==5.13.2
flake8==7.0.0
mypy==1.8.0
```

### 2.3 基础设施

| 组件 | 版本 | 用途 |
|------|------|------|
| PostgreSQL | 15+ | 主数据库 |
| Redis | 7+ | 缓存、Temp ID |
| Nginx | 1.24+ | 反向代理、SSL |

---

## 3. 实现阶段

### Phase 1: 基础设施搭建 (Day 1-2)

**目标**: 搭建项目框架，数据库连接，基础配置

| 任务 | 工时 | 产出 |
|------|------|------|
| 项目初始化 | 2h | 项目结构、requirements |
| 配置管理 | 2h | config.py、环境变量 |
| 数据库连接 | 3h | database.py、SQLAlchemy 配置 |
| 数据库迁移 | 3h | Alembic 配置、初始迁移 |
| Docker 配置 | 2h | Dockerfile、docker-compose |

**验收标准**:
- [ ] `docker-compose up` 成功启动 PostgreSQL + Redis
- [ ] Alembic 迁移成功执行
- [ ] 基础健康检查接口 `/health` 返回 OK

---

### Phase 2: 核心模型与 Service (Day 3-5)

**目标**: 完成所有数据模型和基础 Service

| 任务 | 工时 | 依赖 |
|------|------|------|
| Device Model | 2h | Phase 1 |
| Device Service | 4h | Device Model |
| Temp ID Model | 2h | Phase 1 |
| Temp ID Service | 3h | Temp ID Model |
| Presence Model | 2h | Phase 1 |
| Presence Service | 4h | Presence Model, Temp ID Service |
| Message Model | 2h | Phase 1 |
| Session Model | 2h | Phase 1 |
| Messaging Service | 6h | Message Model, Session Model |
| Friendship Model | 2h | Phase 1 |
| Block Model | 1h | Phase 1 |
| Relation Service | 5h | Friendship Model, Block Model |

**验收标准**:
- [ ] 所有模型可通过 Alembic 创建表
- [ ] 每个 Service 的单元测试通过
- [ ] Temp ID 生成和解析正确

---

### Phase 3: REST API 实现 (Day 6-8)

**目标**: 完成所有 REST API 端点

| 任务 | 工时 | 依赖 |
|------|------|------|
| Device Router | 3h | Device Service |
| Temp ID Router | 2h | Temp ID Service |
| Presence Router | 3h | Presence Service |
| Message Router | 4h | Messaging Service |
| Friendship Router | 4h | Relation Service |
| 统一响应格式 | 2h | - |
| 错误处理 | 2h | - |
| 输入验证 | 2h | - |

**API 端点清单**:

```
POST   /api/v1/device/init
GET    /api/v1/device/{device_id}
PUT    /api/v1/device/{device_id}

POST   /api/v1/temp-id/refresh

POST   /api/v1/presence/resolve
POST   /api/v1/presence/disconnect

POST   /api/v1/messages
GET    /api/v1/messages/{session_id}
POST   /api/v1/messages/read

GET    /api/v1/friends
POST   /api/v1/friends/request
PUT    /api/v1/friends/{request_id}
DELETE /api/v1/friends/{friend_device_id}

POST   /api/v1/block
DELETE /api/v1/block/{target_device_id}
```

**验收标准**:
- [ ] 所有 API 端点可通过 curl/Postman 调用
- [ ] 统一响应格式符合 API Contract
- [ ] 错误码正确返回

---

### Phase 4: WebSocket 实现 (Day 9-10)

**目标**: 完成 WebSocket 实时通信

| 任务 | 工时 | 依赖 |
|------|------|------|
| WebSocket Manager | 4h | Phase 2 |
| WebSocket Router | 2h | WebSocket Manager |
| 消息推送逻辑 | 3h | Messaging Service |
| Boost 推送 | 2h | Presence Service |
| 好友申请推送 | 2h | Relation Service |
| 心跳处理 | 1h | - |

**WebSocket 事件**:

```python
# Client -> Server
{"action": "send_message", "payload": {...}}
{"action": "mark_read", "payload": {...}}
{"action": "ping"}

# Server -> Client
{"type": "connected", "payload": {...}}
{"type": "new_message", "payload": {...}}
{"type": "message_sent", "payload": {...}}
{"type": "friend_request", "payload": {...}}
{"type": "friend_response", "payload": {...}}
{"type": "boost", "payload": {...}}
{"type": "session_expired", "payload": {...}}
{"type": "messages_read", "payload": {...}}
{"type": "pong"}
{"type": "error", "payload": {...}}
```

**验收标准**:
- [ ] WebSocket 连接成功
- [ ] 消息实时推送延迟 < 100ms
- [ ] 断线重连处理正确

---

### Phase 5: 集成测试与 Bugfix (Day 11-12)

**目标**: 完整测试覆盖，修复问题

| 任务 | 工时 |
|------|------|
| 单元测试补全 | 4h |
| 集成测试 | 6h |
| E2E 测试 | 4h |
| Bug 修复 | 6h |

**测试覆盖目标**:
- [ ] 单元测试覆盖率 > 80%
- [ ] 所有 P0 测试用例通过
- [ ] 关键场景 E2E 测试通过

---

### Phase 6: 性能优化与部署 (Day 13-14)

**目标**: 性能调优，生产部署

| 任务 | 工时 |
|------|------|
| 数据库查询优化 | 3h |
| 缓存策略实现 | 3h |
| 连接池配置 | 2h |
| 日志配置 | 2h |
| 监控接入 | 2h |
| 生产部署 | 4h |

**性能目标**:
- [ ] API 平均响应 < 100ms
- [ ] WebSocket 消息延迟 < 50ms
- [ ] 支持 1000+ 并发连接

---

## 4. 数据库设计

### 4.1 ER 图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   devices   │◄──────┤  temp_ids   │       │   blocks    │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ device_id   │◄──────┤ temp_id     │       │ blocker_id  │
│ nickname    │       │ device_id   │       │ target_id   │
│ avatar      │       │ expires_at  │       └─────────────┘
│ tags        │       └─────────────┘
│ profile     │            │
│ is_anonymous├────────────┘
│ role_name   │
└──────┬──────┘
       │
       │    ┌─────────────┐       ┌─────────────┐
       └───►│ friendships │◄──────┤  sessions   │
            ├─────────────┤       ├─────────────┤
            │ request_id  │       │ session_id  │
            │ user_id     │       │ user1_id    │
            │ friend_id   │       │ user2_id    │
            │ status      │       │ is_temp     │
            │ message     │       │ expired_at  │
            └─────────────┘       └──────┬──────┘
                                         │
                                    ┌────┴────┐
                                    │ messages│
                                    ├─────────┤
                                    │message_id
                                    │session_id
                                    │sender_id
                                    │receiver_id
                                    │content
                                    │type
                                    │status
                                    └─────────┘

┌─────────────┐
│  presence   │
├─────────────┤
│ user_id     │
│ nearby_user_id
│ last_seen_at│
│ last_disconnect_at
│ last_boost_at
└─────────────┘
```

### 4.2 建表 SQL

```sql
-- devices 表
CREATE TABLE devices (
    device_id UUID PRIMARY KEY,
    nickname VARCHAR(50) NOT NULL,
    avatar VARCHAR(500),
    tags TEXT[] DEFAULT '{}',
    profile VARCHAR(200) DEFAULT '',
    is_anonymous BOOLEAN DEFAULT FALSE,
    role_name VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_devices_nickname ON devices(nickname);

-- temp_ids 表
CREATE TABLE temp_ids (
    temp_id CHAR(32) PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_temp_ids_device_id ON temp_ids(device_id);
CREATE INDEX idx_temp_ids_expires_at ON temp_ids(expires_at);

-- presence 表
CREATE TABLE presence (
    user_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    nearby_user_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_disconnect_at TIMESTAMP WITH TIME ZONE,
    last_boost_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (user_id, nearby_user_id)
);

CREATE INDEX idx_presence_user_id ON presence(user_id);
CREATE INDEX idx_presence_nearby_user_id ON presence(nearby_user_id);
CREATE INDEX idx_presence_last_seen ON presence(last_seen_at);

-- sessions 表
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user1_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    user2_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    is_temp BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expired_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (user1_id, user2_id)
);

CREATE INDEX idx_sessions_user1 ON sessions(user1_id);
CREATE INDEX idx_sessions_user2 ON sessions(user2_id);
CREATE INDEX idx_sessions_temp ON sessions(is_temp, expired_at);

-- messages 表
CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    receiver_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    content VARCHAR(1000) NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'common',
    status VARCHAR(20) NOT NULL DEFAULT 'sent',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    read_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_messages_session ON messages(session_id, created_at DESC);
CREATE INDEX idx_messages_sender ON messages(sender_id, created_at DESC);
CREATE INDEX idx_messages_receiver ON messages(receiver_id, status);

-- friendships 表
CREATE TABLE friendships (
    request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    friend_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    message VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (user_id, friend_id)
);

CREATE INDEX idx_friendships_user ON friendships(user_id, status);
CREATE INDEX idx_friendships_friend ON friendships(friend_id, status);
CREATE INDEX idx_friendships_status ON friendships(status, updated_at);

-- blocks 表
CREATE TABLE blocks (
    blocker_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (blocker_id, target_id)
);

CREATE INDEX idx_blocks_target ON blocks(target_id);
```

---

## 5. API 实现顺序

### 推荐实现顺序（依赖关系）

```
Day 3: Device Service + Router
  │
  ▼
Day 4: Temp ID Service + Router
  │
  ▼
Day 5: Presence Service + Router
  │    (依赖: Device, Temp ID)
  ▼
Day 6: Messaging Service + Router
  │    (依赖: Device, Session)
  ▼
Day 7: Relation Service + Router
       (依赖: Device, Friendship, Block)
  │
  ▼
Day 8: WebSocket (依赖所有 Service)
```

---

## 6. WebSocket 实现细节

### 6.1 Connection Manager

```python
# app/services/websocket_manager.py
from typing import Dict, Optional
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
    
    async def connect(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.connections[device_id] = websocket
        # 发送连接确认
        await self.send_message(device_id, {
            "type": "connected",
            "payload": {
                "device_id": device_id,
                "server_time": datetime.utcnow().isoformat()
            }
        })
    
    def disconnect(self, device_id: str):
        self.connections.pop(device_id, None)
    
    async def send_message(self, device_id: str, message: dict) -> bool:
        websocket = self.connections.get(device_id)
        if websocket:
            await websocket.send_json(message)
            return True
        return False
    
    async def broadcast(self, device_ids: list, message: dict):
        for device_id in device_ids:
            await self.send_message(device_id, message)

# 全局实例
ws_manager = WebSocketManager()
```

### 6.2 WebSocket Router

```python
# app/routers/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    device_id: str = Query(...)
):
    await ws_manager.connect(device_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await handle_client_message(device_id, data)
    except WebSocketDisconnect:
        ws_manager.disconnect(device_id)

async def handle_client_message(device_id: str, data: dict):
    action = data.get("action")
    payload = data.get("payload", {})
    
    if action == "send_message":
        result = await messaging_service.send_message(
            sender_id=device_id,
            receiver_id=payload["receiver_id"],
            content=payload["content"],
            type=payload.get("type", "common")
        )
        # 推送确认给发送者
        await ws_manager.send_message(device_id, {
            "type": "message_sent",
            "payload": result
        })
    
    elif action == "mark_read":
        count = await messaging_service.mark_messages_read(
            device_id=device_id,
            message_ids=payload["message_ids"]
        )
    
    elif action == "ping":
        await ws_manager.send_message(device_id, {"type": "pong"})
```

---

## 7. 测试策略

### 7.1 测试金字塔

```
        /\
       /  \
      / E2E \          <- 5% (关键场景)
     /________\
    /          \
   / Integration \     <- 25% (API 测试)
  /______________\
 /                \
/      Unit        \   <- 70% (Service 测试)
/____________________\
```

### 7.2 测试文件结构

```
tests/
├── conftest.py              # 共享 fixture
├── unit/
│   ├── test_device_service.py
│   ├── test_temp_id_service.py
│   ├── test_presence_service.py
│   ├── test_messaging_service.py
│   └── test_relation_service.py
├── integration/
│   ├── test_device_api.py
│   ├── test_presence_api.py
│   ├── test_messaging_api.py
│   ├── test_friendship_api.py
│   └── test_websocket.py
└── e2e/
    ├── test_first_meeting.py
    ├── test_become_friends.py
    └── test_boost_reunion.py
```

### 7.3 关键 Fixture

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def device_a(client):
    """创建测试设备 A"""
    response = await client.post("/api/v1/device/init", json={
        "device_id": "550e8400-e29b-41d4-a716-446655440001",
        "nickname": "User A",
        "tags": ["测试"],
        "profile": "我是用户A"
    })
    return response.json()["data"]

@pytest.fixture
async def device_b(client):
    """创建测试设备 B"""
    response = await client.post("/api/v1/device/init", json={
        "device_id": "550e8400-e29b-41d4-a716-446655440002",
        "nickname": "User B",
        "tags": ["测试"],
        "profile": "我是用户B"
    })
    return response.json()["data"]
```

---

## 8. 部署计划

### 8.1 环境规划

| 环境 | 用途 | 配置 |
|------|------|------|
| Local | 开发 | Docker Compose |
| Dev | 联调 | 1 vCPU, 2GB RAM |
| Staging | 测试 | 2 vCPU, 4GB RAM |
| Prod | 生产 | 4 vCPU, 8GB RAM |

### 8.2 Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/notepassing
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=notepassing
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app

volumes:
  postgres_data:
  redis_data:
```

### 8.3 部署检查清单

**部署前**:
- [ ] 代码审查通过
- [ ] 所有 P0 测试通过
- [ ] 环境变量配置正确
- [ ] 数据库迁移脚本准备就绪

**部署中**:
- [ ] 数据库备份
- [ ] 执行 Alembic 迁移
- [ ] 启动新实例
- [ ] 健康检查通过
- [ ] 切换流量

**部署后**:
- [ ] 监控告警正常
- [ ] 错误率 < 0.1%
- [ ] 响应时间正常
- [ ] 日志无异常

---

## 9. 里程碑与交付物

### 里程碑

| 日期 | 里程碑 | 交付物 |
|------|--------|--------|
| Day 2 | 基础设施完成 | 可运行的基础服务 |
| Day 5 | 核心 Service 完成 | 所有 Service + 单元测试 |
| Day 8 | REST API 完成 | 所有 HTTP 接口 |
| Day 10 | WebSocket 完成 | 实时通信功能 |
| Day 12 | 测试完成 | 测试报告，Bug 修复 |
| Day 14 | MVP 发布 | 生产环境上线 |

### 交付物清单

- [ ] 源代码仓库
- [ ] API 文档 (自动生成的 OpenAPI/Swagger)
- [ ] 部署文档
- [ ] 测试报告
- [ ] 监控告警配置
- [ ] 运维手册

---

## 10. 风险与应对

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|----------|
| WebSocket 并发性能不足 | 中 | 高 | 提前压测，准备水平扩展方案 |
| 数据库查询慢 | 中 | 中 | 预留优化时间，准备索引优化 |
| Temp ID 冲突 | 低 | 高 | 使用 UUID + 时间戳 + 随机数 |
| 蓝牙范围判断不准确 | 高 | 低 | 由客户端负责主要判断逻辑 |
| 客户端对接延迟 | 中 | 中 | 提前提供 Mock API |
