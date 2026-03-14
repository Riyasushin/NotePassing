# NotePassing 部署与测试指南

## 一、部署方式

### 方式1：使用 Docker Compose（推荐）

```bash
# 1. 进入后端目录
cd /home/rj/WorkingOn/Hackathon-NotePassing/backend

# 2. 启动服务（PostgreSQL + Backend）
docker-compose up -d

# 3. 查看日志
docker-compose logs -f backend

# 4. 停止服务
docker-compose down
```

### 方式2：本地运行

```bash
# 1. 进入后端目录
cd /home/rj/WorkingOn/Hackathon-NotePassing/backend

# 2. 创建虚拟环境
uv venv --python python3.10

# 3. 安装依赖
uv pip install -e ".[dev]"

# 4. 设置环境变量（使用 SQLite）
export DATABASE_URL="sqlite+aiosqlite:///./app.db"
export DEBUG="true"
export SECRET_KEY="your-secret-key"

# 5. 启动服务器
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 二、连接测试

### 测试1：健康检查

```bash
curl http://localhost:8000/health
```

**预期输出：**
```json
{"status":"ok","version":"1.0.0"}
```

---

### 测试2：完整业务流程

#### Step 1: 初始化设备 A

```bash
curl -X POST http://localhost:8000/api/v1/device/init \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "nickname": "Alice",
    "tags": ["coffee", "music"],
    "profile": "我喜欢咖啡！"
  }'
```

**预期输出：**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "device_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "nickname": "Alice",
    "is_new": true,
    "created_at": "2026-03-14T10:00:00Z"
  }
}
```

#### Step 2: 初始化设备 B

```bash
curl -X POST http://localhost:8000/api/v1/device/init \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "nickname": "Bob",
    "tags": ["sports", "travel"],
    "profile": "旅行爱好者"
  }'
```

**预期输出：**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "device_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "nickname": "Bob",
    "is_new": true,
    "created_at": "2026-03-14T10:00:00Z"
  }
}
```

#### Step 3: B 获取 Temp ID（BLE 广播用）

```bash
curl -X POST http://localhost:8000/api/v1/temp-id/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  }'
```

**预期输出：**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "temp_id": "a1b2c3d4e5f6789012345678abcdef01",
    "expires_at": "2026-03-14T10:10:00Z"
  }
}
```

#### Step 4: A 查看 B 的资料

```bash
curl "http://localhost:8000/api/v1/device/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb?requester_id=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
```

**预期输出：**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "device_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "nickname": "Bob",
    "avatar": null,
    "tags": ["sports", "travel"],
    "profile": "旅行爱好者",
    "is_anonymous": false,
    "role_name": null,
    "is_friend": false
  }
}
```

#### Step 5: A 给 B 发送消息（陌生人聊天）

```bash
curl -X POST http://localhost:8000/api/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "receiver_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "content": "你好 Bob！想聊天吗？",
    "type": "common"
  }'
```

**预期输出：**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "message_id": "550e8400-e29b-41d4-a716-446655440000",
    "session_id": "550e8400-e29b-41d4-a716-446655440001",
    "status": "sent",
    "created_at": "2026-03-14T10:00:00Z"
  }
}
```

**记录 session_id，后续会用到**

#### Step 6: B 回复 A

```bash
curl -X POST http://localhost:8000/api/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "receiver_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "content": "你好 Alice！很高兴认识你！",
    "type": "common"
  }'
```

**预期输出：**类似 Step 5，状态为 "sent"

#### Step 7: 查看聊天记录

```bash
# 使用 Step 5 返回的 session_id
curl "http://localhost:8000/api/v1/messages/550e8400-e29b-41d4-a716-446655440001?device_id=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa&limit=20"
```

**预期输出：**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440001",
    "messages": [
      {
        "message_id": "...",
        "sender_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "content": "你好 Bob！想聊天吗？",
        "type": "common",
        "status": "sent",
        "created_at": "2026-03-14T10:00:00Z"
      },
      {
        "message_id": "...",
        "sender_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "content": "你好 Alice！很高兴认识你！",
        "type": "common",
        "status": "sent",
        "created_at": "2026-03-14T10:00:01Z"
      }
    ],
    "has_more": false
  }
}
```

#### Step 8: A 发送好友申请

```bash
curl -X POST http://localhost:8000/api/v1/friends/request \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "receiver_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "message": "我们成为好友吧！"
  }'
```

**预期输出：**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "request_id": "550e8400-e29b-41d4-a716-446655440002",
    "status": "pending",
    "created_at": "2026-03-14T10:00:00Z"
  }
}
```

**记录 request_id**

#### Step 9: B 接受好友申请

```bash
# 使用 Step 8 返回的 request_id
curl -X PUT http://localhost:8000/api/v1/friends/550e8400-e29b-41d4-a716-446655440002 \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "action": "accept"
  }'
```

**预期输出：**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "request_id": "550e8400-e29b-41d4-a716-446655440002",
    "status": "accepted",
    "friend": {
      "device_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "nickname": "Alice",
      "avatar": null
    },
    "session_id": "550e8400-e29b-41d4-a716-446655440003"
  }
}
```

#### Step 10: A 查看好友列表

```bash
curl "http://localhost:8000/api/v1/friends?device_id=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
```

**预期输出：**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "friends": [
      {
        "device_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "nickname": "Bob",
        "avatar": null,
        "tags": ["sports", "travel"],
        "profile": "旅行爱好者",
        "is_anonymous": false,
        "last_chat_at": null
      }
    ]
  }
}
```

#### Step 11: A 和 B 作为好友发送消息（无限制）

```bash
curl -X POST http://localhost:8000/api/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "receiver_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "content": "现在我们是好友了！",
    "type": "common"
  }'
```

**预期输出：**消息发送成功，没有 2 条限制

#### Step 12: A 屏蔽 B

```bash
curl -X POST http://localhost:8000/api/v1/block \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "target_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  }'
```

**预期输出：**
```json
{
  "code": 0,
  "message": "ok",
  "data": null
}
```

#### Step 13: B 尝试给 A 发送消息（应该失败）

```bash
curl -X POST http://localhost:8000/api/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "receiver_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "content": "你能收到吗？",
    "type": "common"
  }'
```

**预期输出：**
```json
{
  "code": 4004,
  "message": "已被对方屏蔽",
  "data": null
}
```

---

## 三、WebSocket 测试

### 使用 wscat

```bash
# 安装 wscat
npm install -g wscat

# 连接 WebSocket
wscat -c "ws://localhost:8000/api/v1/ws?device_id=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

# 发送 ping
> {"action": "ping"}
# 预期收到: {"type": "pong"}

# 发送消息
> {"action": "send_message", "payload": {"receiver_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "content": "WebSocket 消息！", "type": "common"}}
# 预期收到: {"type": "message_sent", ...}
```

### 使用 curl 测试 WebSocket 连接（不支持，WebSocket 需要专用客户端）

---

## 四、一键测试脚本

```bash
# 给脚本执行权限
chmod +x tests/e2e/manual_test.sh

# 运行测试
./tests/e2e/manual_test.sh
```

---

## 五、常见问题

### 问题1：连接被拒绝

```
curl: (7) Failed to connect to localhost port 8000: Connection refused
```

**解决：**
```bash
# 检查服务器是否运行
curl http://localhost:8000/health

# 如果没有响应，重新启动服务器
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 问题2：数据库连接错误

**解决（使用 SQLite）：**
```bash
export DATABASE_URL="sqlite+aiosqlite:///./app.db"
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 问题3：返回 500 错误

**解决：**
```bash
# 查看服务器日志
docker-compose logs -f backend
# 或
uv run uvicorn app.main:app --reload --log-level debug
```

---

## 六、API 文档

启动服务器后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
