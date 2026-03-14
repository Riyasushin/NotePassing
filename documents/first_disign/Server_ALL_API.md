# NotePassing Server API 完整文档

> 本文档基于 `unified_api_contract.md` 编写，描述 Server 端所有 API 的详细实现规范。

---

## 目录

1. [通用规范](#1-通用规范)
2. [Device Service](#2-device-service)
3. [Temp ID Service](#3-temp-id-service)
4. [Presence Service](#4-presence-service)
5. [Messaging Service](#5-messaging-service)
6. [Relation Service](#6-relation-service)
7. [WebSocket 协议](#7-websocket-协议)
8. [数据模型](#8-数据模型)
9. [错误处理](#9-错误处理)
10. [测试规范](#10-测试规范)

---


## 1. 通用规范

### 1.1 基础信息

| 项目 | 值 |
|------|-----|
| 基础路径 | `/api/v1` |
| 协议 | HTTPS（REST） / WSS（WebSocket） |
| 数据格式 | JSON（`Content-Type: application/json`） |
| 编码 | UTF-8 |
| 时间格式 | ISO 8601（`2026-03-14T10:53:00Z`） |

### 1.2 统一响应格式

**成功响应（HTTP 200）:**

```json
{
    "code": 0,
    "message": "ok",
    "data": { ... }
}
```

**错误响应:**

```json
{
    "code": 4001,
    "message": "临时聊天消息已达上限",
    "data": null
}
```

### 1.3 认证方式

- 无传统认证，设备 ID 即身份标识
- `device_id` 通过请求体或查询参数传递
- 所有接口需校验 `device_id` 格式（UUID v4）

---

## 2. Device Service

### 2.1 设备初始化

创建或恢复设备记录。

```
POST /api/v1/device/init
```

**请求体:**

```json
{
    "device_id": "550e8400-e29b-41d4-a716-446655440000",
    "nickname": "默认昵称",
    "tags": [],
    "profile": ""
}
```

**字段说明:**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| device_id | string | ✓ | UUID v4 格式，32位十六进制 |
| nickname | string | ✓ | 最长 50 字符 |
| tags | string[] | ✗ | 标签列表，每项最长 20 字符 |
| profile | string | ✗ | 最长 200 字符 |
| avatar | string | ✗ | 头像 URL |
| is_anonymous | boolean | ✗ | 是否匿名模式，默认 false |
| role_name | string | ✗ | 匿名角色名，最长 50 字符 |

**成功响应:**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "device_id": "550e8400-e29b-41d4-a716-446655440000",
        "nickname": "默认昵称",
        "is_new": true,
        "created_at": "2026-03-14T10:53:00Z"
    }
}
```

**服务端逻辑:**
1. 校验 `device_id` 格式，无效返回 5001
2. 查询数据库，若存在则返回 `is_new: false`
3. 若不存在则创建记录，返回 `is_new: true`
4. 初始化设备默认设置

---

### 2.2 获取设备资料

```
GET /api/v1/device/{device_id}?requester_id={requester_id}
```

**路径参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| device_id | string | 目标设备 ID |

**查询参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| requester_id | string | ✓ | 请求者 device_id |

**成功响应:**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "device_id": "target_uuid",
        "nickname": "小明",
        "avatar": "https://cdn.example.com/avatar.jpg",
        "tags": ["摄影", "ACG"],
        "profile": "喜欢拍照",
        "is_anonymous": false,
        "role_name": null,
        "is_friend": true
    }
}
```

**服务端逻辑:**
1. 校验 `requester_id` 是否存在，不存在返回 4007
2. 查询目标设备资料
3. 根据隐私规则过滤字段：
   - 陌生人且匿名模式：隐藏 avatar
   - 陌生人：不显示真实 device_id
4. 查询双方好友关系，设置 `is_friend`

---

### 2.3 更新设备资料

```
PUT /api/v1/device/{device_id}
```

**请求体（部分更新）:**

```json
{
    "nickname": "新昵称",
    "avatar": "https://cdn.example.com/new-avatar.jpg",
    "tags": ["摄影", "旅行"],
    "profile": "新简介",
    "is_anonymous": false,
    "role_name": "神秘旅者"
}
```

**字段约束:**

| 字段 | 类型 | 约束 |
|------|------|------|
| nickname | string | 最长 50 字符 |
| avatar | string | URL 格式 |
| tags | string[] | 最多 10 个标签，每项最长 20 字符 |
| profile | string | 最长 200 字符 |
| is_anonymous | boolean | - |
| role_name | string | 最长 50 字符，仅在匿名模式显示 |

**成功响应:**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "device_id": "550e8400...",
        "nickname": "新昵称",
        "avatar": "https://cdn.example.com/new-avatar.jpg",
        "tags": ["摄影", "旅行"],
        "profile": "新简介",
        "is_anonymous": false,
        "role_name": "神秘旅者",
        "updated_at": "2026-03-14T11:00:00Z"
    }
}
```

**服务端逻辑:**
1. 校验 device_id 是否存在
2. 校验各字段格式
3. 更新数据库记录
4. 更新 Redis 缓存（如有）

---

## 3. Temp ID Service

### 3.1 刷新临时 ID

```
POST /api/v1/temp-id/refresh
```

**请求体:**

```json
{
    "device_id": "my_device_uuid",
    "current_temp_id": "old_temp_id_hex"
}
```

**字段说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 自身设备 ID |
| current_temp_id | string | ✗ | 当前使用的 temp_id |

**成功响应:**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "temp_id": "a1b2c3d4e5f6...",
        "expires_at": "2026-03-14T11:00:00Z"
    }
}
```

**服务端逻辑:**
1. 校验 device_id 是否已初始化
2. 生成新的 temp_id：
   ```python
   temp_id = hex(hash(device_id + secret_key + timestamp + random_salt))
   ```
3. 存入 temp_ids 表，设置 10 分钟后过期
4. 若传入 `current_temp_id`，将其过期时间缩短至 5 分钟后（缓冲期）
5. 返回新的 temp_id 和过期时间

---

## 4. Presence Service

### 4.1 解析附近设备

```
POST /api/v1/presence/resolve
```

**请求体:**

```json
{
    "device_id": "my_device_uuid",
    "scanned_devices": [
        { "temp_id": "abc123def456...", "rssi": -65 },
        { "temp_id": "789xyz000111...", "rssi": -80 }
    ]
}
```

**字段说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 自身设备 ID |
| scanned_devices | array | ✓ | BLE 扫描结果 |
| scanned_devices[].temp_id | string | ✓ | 临时 ID |
| scanned_devices[].rssi | int | ✓ | 信号强度 dBm |

**成功响应:**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "nearby_devices": [
            {
                "temp_id": "abc123def456...",
                "device_id": "resolved_uuid",
                "nickname": "小明",
                "avatar": "https://cdn.example.com/avatar.jpg",
                "tags": ["摄影", "旅行"],
                "profile": "喜欢拍照的程序员",
                "is_anonymous": false,
                "role_name": null,
                "distance_estimate": 2.5,
                "is_friend": false
            }
        ],
        "boost_alerts": [
            {
                "device_id": "friend_uuid",
                "nickname": "好友昵称",
                "distance_estimate": 3.0
            }
        ]
    }
}
```

**服务端逻辑:**

1. **解析 temp_id：**
   - 查询 temp_ids 表，将 temp_id 解析为 device_id
   - 无效的 temp_id 跳过，记录日志

2. **过滤屏蔽用户：**
   - 查询 block 表，过滤被屏蔽和屏蔽方的设备

3. **计算距离：**
   ```python
   # RSSI 转距离估算（简化模型）
   def rssi_to_distance(rssi):
       tx_power = -59  # 1米处的 RSSI 参考值
       n = 2.0  # 环境衰减因子
       distance = 10 ** ((tx_power - rssi) / (10 * n))
       return round(distance, 1)
   ```

4. **隐私过滤：**
   - 陌生人 + 匿名模式：隐藏 avatar
   - 陌生人：不返回真实 device_id（仅在好友时返回）

5. **更新 presence 表：**
   - 记录谁在谁附近
   - 更新最后发现时间

6. **检测 Boost：**
   - 检查好友是否从"不在附近"变为"在附近"
   - 距上次 Boost ≥ 5 分钟才触发
   - 更新好友最后 Boost 时间

---

### 4.2 上报离开范围

```
POST /api/v1/presence/disconnect
```

**请求体:**

```json
{
    "device_id": "my_device_uuid",
    "left_device_id": "target_device_uuid"
}
```

**字段说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 自身设备 ID |
| left_device_id | string | ✓ | 离开的设备 ID |

**成功响应:**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "session_expired": true,
        "session_id": "uuid-of-expired-session"
    }
}
```

**服务端逻辑:**
1. 更新 presence 表，`is_online = false`
2. 查询是否存在临时会话（`is_temp = true`）
3. 若存在，标记会话为过期
4. 通过 WebSocket 向双方推送 `session_expired` 事件

---

## 5. Messaging Service

### 5.1 发送消息（HTTP 备用）

WebSocket 不可用时使用。

```
POST /api/v1/messages
```

**请求体:**

```json
{
    "sender_id": "my_device_uuid",
    "receiver_id": "target_device_uuid",
    "content": "你好",
    "type": "common"
}
```

**字段说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sender_id | string | ✓ | 发送者 device_id |
| receiver_id | string | ✓ | 接收者 device_id |
| content | string | ✓ | 消息内容，最长 1000 字符 |
| type | string | ✓ | `common` 或 `heartbeat` |

**成功响应:**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "message_id": "msg-uuid",
        "session_id": "session-uuid",
        "status": "sent",
        "created_at": "2026-03-14T10:53:00Z"
    }
}
```

**服务端逻辑:**

1. **参数校验：**
   - 校验 device_id 格式
   - 校验 content 长度

2. **权限检查：**
   - 检查 sender 是否被 receiver 屏蔽 → 4004
   - 检查 receiver 是否被 sender 屏蔽 → 4004

3. **好友关系检查：**
   - 是好友：无限制
   - 非好友：检查临时会话限制

4. **临时会话限制：**
   ```python
   def check_temp_message_limit(sender_id, receiver_id):
       if is_friend(sender_id, receiver_id):
           return True
       
       session = get_temp_session(sender_id, receiver_id)
       if not session:
           # 创建新临时会话
           session = create_temp_session(sender_id, receiver_id)
           return True
       
       if session.is_expired:
           return False  # 4002
       
       # 统计未回复消息数
       count = messages.count(
           sender_id=sender_id,
           receiver_id=receiver_id,
           session_id=session.id,
           created_at > session.created_at
       )
       
       if count >= 2:
           return False  # 4001
       
       return True
   ```

5. **存储消息：**
   - 生成 message_id（UUID）
   - 存入 messages 表
   - 更新会话最后消息时间

6. **实时推送：**
   - 通过 WebSocket 推送给接收者（若在线）
   - 不在线则等待拉取

---

### 5.2 获取历史消息

```
GET /api/v1/messages/{session_id}?device_id={device_id}&before={before}&limit={limit}
```

**路径参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| session_id | string | 会话 ID |

**查询参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 请求者 device_id |
| before | string | ✗ | 分页游标（ISO 8601） |
| limit | int | ✗ | 每页条数，默认 20，最大 50 |

**成功响应:**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "session_id": "session-uuid",
        "messages": [
            {
                "message_id": "msg-uuid",
                "sender_id": "device-uuid",
                "content": "你好",
                "type": "common",
                "status": "read",
                "created_at": "2026-03-14T10:50:00Z"
            }
        ],
        "has_more": true
    }
}
```

**服务端逻辑:**
1. 校验 device_id 是否有权限访问该会话
2. 按时间倒序查询消息
3. 支持游标分页

---

### 5.3 标记消息已读

```
POST /api/v1/messages/read
```

**请求体:**

```json
{
    "device_id": "my_device_uuid",
    "message_ids": ["msg-uuid-1", "msg-uuid-2"]
}
```

**字段说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 操作者 device_id |
| message_ids | string[] | ✓ | 消息 ID 列表，最多 100 条 |

**成功响应:**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "updated_count": 2
    }
}
```

**服务端逻辑:**
1. 批量更新 messages 表
2. 设置 `status = read`, `read_at = now()`
3. 通过 WebSocket 通知发送者已读

---

## 6. Relation Service

### 6.1 获取好友列表

```
GET /api/v1/friends?device_id={device_id}
```

**查询参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 自身 device_id |

**成功响应:**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "friends": [
            {
                "device_id": "friend_uuid",
                "nickname": "好友昵称",
                "avatar": "https://cdn.example.com/avatar.jpg",
                "tags": ["摄影"],
                "profile": "简介",
                "is_anonymous": false,
                "last_chat_at": "2026-03-14T10:00:00Z"
            }
        ]
    }
}
```

**服务端逻辑:**
1. 查询 friendships 表，status = accepted
2. 关联 devices 表获取好友资料
3. 按最后聊天时间倒序排序

---

### 6.2 发送好友申请

```
POST /api/v1/friends/request
```

**请求体:**

```json
{
    "sender_id": "my_device_uuid",
    "receiver_id": "target_device_uuid",
    "message": "想加你为好友"
}
```

**字段说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sender_id | string | ✓ | 申请者 device_id |
| receiver_id | string | ✓ | 目标 device_id |
| message | string | ✗ | 验证消息，最长 200 字符 |

**成功响应:**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "request_id": "friendship-uuid",
        "status": "pending",
        "created_at": "2026-03-14T10:53:00Z"
    }
}
```

**服务端逻辑:**

1. **权限检查：**
   - 检查 sender 是否被 receiver 屏蔽 → 4004
   - 检查 receiver 是否被 sender 屏蔽 → 4004

2. **冷却检查：**
   ```python
   def check_friend_request_cooldown(sender_id, receiver_id):
       last_rejection = friendships.find(
           device_a_id=min(sender_id, receiver_id),
           device_b_id=max(sender_id, receiver_id),
           status='rejected'
       ).order_by('-updated_at').first()
       
       if last_rejection and (now() - last_rejection.updated_at) < 24h:
           return False  # 4005
       return True
   ```

3. **重复检查：**
   - 检查是否存在 pending 状态的申请 → 4009

4. **创建记录：**
   - 创建 friendships 记录，status = pending
   - 通过 WebSocket 推送 `friend_request` 给接收方

---

### 6.3 回应好友申请

```
PUT /api/v1/friends/{request_id}
```

**路径参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| request_id | string | 好友申请 ID |

**请求体:**

```json
{
    "device_id": "my_device_uuid",
    "action": "accept"
}
```

**字段说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 操作者 device_id |
| action | string | ✓ | `accept` 或 `reject` |

**成功响应（accept）:**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "request_id": "friendship-uuid",
        "status": "accepted",
        "friend": {
            "device_id": "friend_uuid",
            "nickname": "新好友",
            "avatar": "url"
        },
        "session_id": "permanent-session-uuid"
    }
}
```

**成功响应（reject）:**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "request_id": "friendship-uuid",
        "status": "rejected"
    }
}
```

**服务端逻辑:**

**Accept 流程:**
1. 校验 device_id 是否有权限操作该申请
2. 更新 friendships 状态为 accepted
3. 若存在临时会话，升级为永久会话（`is_temp = false`）
4. 若不存在，创建永久会话
5. 通过 WebSocket 通知申请方

**Reject 流程:**
1. 更新 friendships 状态为 rejected
2. 记录拒绝时间
3. 通过 WebSocket 通知申请方

---

### 6.4 删除好友

```
DELETE /api/v1/friends/{friend_device_id}?device_id={device_id}
```

**路径参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| friend_device_id | string | 好友 device_id |

**查询参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 操作者 device_id |

**成功响应:**

```json
{
    "code": 0,
    "message": "ok",
    "data": null
}
```

**服务端逻辑:**
1. 删除 friendships 记录或标记为 deleted
2. 保留会话和消息记录
3. 可选择是否降级会话为临时会话

---

### 6.5 屏蔽用户

```
POST /api/v1/block
```

**请求体:**

```json
{
    "device_id": "my_device_uuid",
    "target_id": "target_device_uuid"
}
```

**字段说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 操作者 device_id |
| target_id | string | ✓ | 目标 device_id |

**成功响应:**

```json
{
    "code": 0,
    "message": "ok",
    "data": null
}
```

**服务端逻辑:**
1. 检查是否已屏蔽
2. 创建 block 记录
3. 若存在好友关系，删除好友关系
4. 若存在 pending 申请，取消申请

---

### 6.6 取消屏蔽

```
DELETE /api/v1/block/{target_device_id}?device_id={device_id}
```

**路径参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| target_device_id | string | 目标 device_id |

**查询参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 操作者 device_id |

**成功响应:**

```json
{
    "code": 0,
    "message": "ok",
    "data": null
}
```

---

## 7. WebSocket 协议

### 7.1 连接

```
WSS /api/v1/ws?device_id=<device_id>
```

连接成功后服务器推送确认：

```json
{
    "type": "connected",
    "payload": {
        "device_id": "my_device_uuid",
        "server_time": "2026-03-14T10:53:00Z"
    }
}
```

**服务端逻辑:**
1. 从 URL 参数获取 device_id
2. 校验 device_id 是否已初始化
3. 将连接存入 connection manager
4. 更新设备在线状态到 Redis
5. 推送 connected 确认

---

### 7.2 客户端 → 服务器

#### 发送消息

```json
{
    "action": "send_message",
    "payload": {
        "receiver_id": "target_device_uuid",
        "content": "你好",
        "type": "common"
    }
}
```

**服务端处理流程:**
1. 解析 action 和 payload
2. 校验 sender_id（从连接信息获取）
3. 执行与 HTTP 发送消息相同的业务逻辑
4. 返回响应：

```json
{
    "type": "message_sent",
    "payload": {
        "message_id": "msg-uuid",
        "session_id": "session-uuid",
        "status": "sent",
        "created_at": "2026-03-14T10:53:00Z"
    }
}
```

#### 标记已读

```json
{
    "action": "mark_read",
    "payload": {
        "message_ids": ["msg-uuid-1", "msg-uuid-2"]
    }
}
```

#### 心跳保活

客户端每 30 秒发送一次：

```json
{
    "action": "ping"
}
```

服务器响应：

```json
{
    "type": "pong"
}
```

---

### 7.3 服务器 → 客户端

#### 新消息

```json
{
    "type": "new_message",
    "payload": {
        "message_id": "msg-uuid",
        "sender_id": "device-uuid",
        "session_id": "session-uuid",
        "content": "你好",
        "type": "common",
        "created_at": "2026-03-14T10:53:00Z"
    }
}
```

#### 好友申请

```json
{
    "type": "friend_request",
    "payload": {
        "request_id": "friendship-uuid",
        "sender": {
            "device_id": "device-uuid",
            "nickname": "小明",
            "avatar": "url",
            "tags": ["摄影"]
        },
        "message": "想加你为好友"
    }
}
```

#### 好友申请结果

```json
{
    "type": "friend_response",
    "payload": {
        "request_id": "friendship-uuid",
        "status": "accepted",
        "friend": {
            "device_id": "friend-uuid",
            "nickname": "新好友"
        },
        "session_id": "permanent-session-uuid"
    }
}
```

#### Boost 提示

```json
{
    "type": "boost",
    "payload": {
        "device_id": "friend_device_uuid",
        "nickname": "好友昵称",
        "distance_estimate": 2.5,
        "timestamp": "2026-03-14T10:53:00Z"
    }
}
```

#### 临时会话过期

```json
{
    "type": "session_expired",
    "payload": {
        "session_id": "session-uuid",
        "peer_device_id": "other-device-uuid",
        "reason": "out_of_range"
    }
}
```

#### 已读回执

```json
{
    "type": "messages_read",
    "payload": {
        "message_ids": ["msg-uuid-1", "msg-uuid-2"],
        "reader_id": "device-uuid",
        "read_at": "2026-03-14T10:55:00Z"
    }
}
```

---

## 8. 数据模型

### 8.1 数据库表结构

#### devices

```sql
CREATE TABLE devices (
    device_id VARCHAR(32) PRIMARY KEY,
    nickname VARCHAR(50) NOT NULL,
    avatar TEXT,
    tags JSONB DEFAULT '[]',
    profile TEXT,
    is_anonymous BOOLEAN DEFAULT FALSE,
    role_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### friendships

```sql
CREATE TABLE friendships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_a_id VARCHAR(32) NOT NULL,
    device_b_id VARCHAR(32) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- pending, accepted, rejected, blocked
    message TEXT,  -- 申请消息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accepted_at TIMESTAMP,
    UNIQUE(device_a_id, device_b_id),
    CHECK (device_a_id < device_b_id)
);
```

#### sessions

```sql
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_a_id VARCHAR(32) NOT NULL,
    device_b_id VARCHAR(32) NOT NULL,
    is_temp BOOLEAN DEFAULT TRUE,
    last_message_at TIMESTAMP,
    expires_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',  -- active, expired
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(device_a_id, device_b_id),
    CHECK (device_a_id < device_b_id)
);
```

#### messages

```sql
CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_id VARCHAR(32) NOT NULL,
    receiver_id VARCHAR(32) NOT NULL,
    session_id UUID NOT NULL,
    content TEXT NOT NULL,
    type VARCHAR(20) NOT NULL,  -- common, heartbeat
    status VARCHAR(20) DEFAULT 'sent',  -- sent, delivered, read
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP
);
```

#### temp_ids

```sql
CREATE TABLE temp_ids (
    temp_id VARCHAR(64) PRIMARY KEY,
    device_id VARCHAR(32) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### presence

```sql
CREATE TABLE presence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(32) NOT NULL,
    nearby_device_id VARCHAR(32) NOT NULL,
    rssi INTEGER,
    distance_estimate FLOAT,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_online BOOLEAN DEFAULT TRUE,
    last_boost_at TIMESTAMP,
    UNIQUE(device_id, nearby_device_id)
);
```

#### blocks

```sql
CREATE TABLE blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(32) NOT NULL,
    target_id VARCHAR(32) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(device_id, target_id)
);
```

### 8.2 索引

```sql
-- temp_ids
CREATE INDEX idx_temp_id_expires ON temp_ids(temp_id, expires_at);
CREATE INDEX idx_temp_id_device ON temp_ids(device_id);

-- presence
CREATE INDEX idx_presence_device_seen ON presence(device_id, is_online, last_seen_at);
CREATE INDEX idx_presence_nearby ON presence(nearby_device_id, is_online);

-- sessions
CREATE INDEX idx_session_devices ON sessions(device_a_id, device_b_id);
CREATE INDEX idx_session_temp_expires ON sessions(is_temp, expires_at);

-- messages
CREATE INDEX idx_messages_session ON messages(session_id, created_at DESC);
CREATE INDEX idx_messages_receiver ON messages(receiver_id, status, created_at);

-- friendships
CREATE INDEX idx_friendships_device ON friendships(device_a_id, status);
CREATE INDEX idx_friendships_pair ON friendships(device_a_id, device_b_id);

-- blocks
CREATE INDEX idx_blocks_device ON blocks(device_id);
```

---

## 9. 错误处理

### 9.1 错误码定义

| 错误码 | 含义 | HTTP 状态码 | 触发场景 |
|--------|------|-------------|----------|
| 0 | 成功 | 200 | — |
| 4001 | 临时聊天消息已达上限 | 400 | 非好友发送超过 2 条消息 |
| 4002 | 临时会话已过期 | 400 | 蓝牙断开超过 1 分钟后继续发消息 |
| 4003 | 不在蓝牙范围内 | 400 | 尝试向非附近用户发起临时聊天 |
| 4004 | 已被对方屏蔽 | 403 | 向屏蔽自己的用户发消息/好友申请 |
| 4005 | 好友申请冷却中 | 429 | 被拒绝后 24h 内重复申请 |
| 4006 | 无效的临时 ID | 400 | temp_id 已过期或不存在 |
| 4007 | 设备未初始化 | 401 | 未调用 init 就使用其他接口 |
| 4008 | 好友关系不存在 | 404 | 操作不存在的好友关系 |
| 4009 | 重复操作 | 409 | 重复发送好友申请等 |
| 5001 | 参数格式错误 | 400 | device_id 格式错误、必填字段缺失等 |
| 5002 | 服务器内部错误 | 500 | 服务端未预期异常 |

### 9.2 错误响应格式

```json
{
    "code": 4001,
    "message": "临时聊天消息已达上限",
    "data": null
}
```

---

## 10. 测试规范

详见 `tests/` 目录，测试覆盖：

- 单元测试：所有 Service 层方法
- 集成测试：所有 API 接口
- WebSocket 测试：连接、消息收发、事件推送
- 并发测试：消息发送、temp_id 刷新
- 边界测试：消息限制、冷却时间、过期处理

---

## 附录 A：接口清单速查

### REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/device/init` | 设备初始化 |
| GET | `/api/v1/device/{device_id}` | 获取设备资料 |
| PUT | `/api/v1/device/{device_id}` | 更新设备资料 |
| POST | `/api/v1/temp-id/refresh` | 刷新临时 BLE 广播 ID |
| POST | `/api/v1/presence/resolve` | 解析附近设备 |
| POST | `/api/v1/presence/disconnect` | 上报设备离开范围 |
| POST | `/api/v1/messages` | 发送消息（HTTP 备用） |
| GET | `/api/v1/messages/{session_id}` | 获取历史消息 |
| POST | `/api/v1/messages/read` | 标记已读 |
| GET | `/api/v1/friends` | 获取好友列表 |
| POST | `/api/v1/friends/request` | 发送好友申请 |
| PUT | `/api/v1/friends/{request_id}` | 回应好友申请 |
| DELETE | `/api/v1/friends/{friend_device_id}` | 删除好友 |
| POST | `/api/v1/block` | 屏蔽用户 |
| DELETE | `/api/v1/block/{target_device_id}` | 取消屏蔽 |

### WebSocket

| 方向 | type / action | 说明 |
|------|---------------|------|
| C → S | `send_message` | 发送消息 |
| C → S | `mark_read` | 标记已读 |
| C → S | `ping` | 心跳保活 |
| S → C | `connected` | 连接确认 |
| S → C | `message_sent` | 消息发送确认 |
| S → C | `new_message` | 新消息推送 |
| S → C | `friend_request` | 好友申请推送 |
| S → C | `friend_response` | 好友申请结果 |
| S → C | `boost` | 好友重新接近提示 |
| S → C | `session_expired` | 临时会话过期 |
| S → C | `messages_read` | 已读回执 |
| S → C | `pong` | 心跳响应 |
| S → C | `error` | 错误通知 |
