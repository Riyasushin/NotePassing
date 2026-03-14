# NotePassing Server 逻辑动作设计 (Logic Actions)

> 基于 Unified API Contract V2 和 MVP_V2_0314 的 Server 端逻辑设计文档  
> **日期**: 2026-03-14

---

## 目录

1. [架构概述](#1-架构概述)
2. [Service 逻辑动作](#2-service-逻辑动作)
3. [数据模型](#3-数据模型)
4. [关键流程时序](#4-关键流程时序)

---

## 1. 架构概述

### 1.1 核心 Services

| Service | 职责 | 对应 API 章节 |
|---------|------|--------------|
| `DeviceService` | 设备注册、资料管理 | 1. Device Service |
| `TempIdService` | 临时 ID 生成与解析 | 2. Temp ID Service |
| `PresenceService` | 附近关系管理、Boost 检测 | 3. Presence Service |
| `MessagingService` | 消息存储、转发 | 4. Messaging Service |
| `RelationService` | 好友关系、屏蔽管理 | 5. Relation Service |
| `WebSocketManager` | WebSocket 连接管理、消息推送 | 6. WebSocket 协议 |

### 1.2 技术栈

- **框架**: FastAPI (Python)
- **数据库**: PostgreSQL
- **缓存**: Redis
- **实时通信**: WebSocket (原生)

---

## 2. Service 逻辑动作

### 2.1 DeviceService

#### 2.1.1 `init_device(device_id, nickname, tags, profile) -> DeviceInfo`

**逻辑步骤:**

1. **参数校验**
   - 校验 `device_id` 是否为有效 UUID v4 格式 → 失败返回 5001
   - 校验 `nickname` 长度 ≤ 50 字符
   - 校验 `profile` 长度 ≤ 200 字符

2. **数据库查询**
   ```sql
   SELECT * FROM devices WHERE device_id = ?
   ```

3. **分支处理**
   - **设备不存在**:
     - 插入新记录到 `devices` 表
     - `is_new = true`
   - **设备已存在**:
     - 返回现有记录
     - `is_new = false`

4. **返回结果**
   ```json
   {
     "device_id": "uuid",
     "nickname": "昵称",
     "is_new": true/false,
     "created_at": "2026-03-14T10:53:00Z"
   }
   ```

---

#### 2.1.2 `get_device_profile(target_id, requester_id) -> Profile`

**逻辑步骤:**

1. **查询目标设备资料**
   ```sql
   SELECT * FROM devices WHERE device_id = ?
   ```

2. **查询关系状态**
   ```sql
   SELECT status FROM friendships 
   WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)
   ```

3. **隐私过滤**
   - 若 `is_friend = true`: 返回完整资料
   - 若 `is_friend = false` 且 `is_anonymous = true`:
     - 隐藏 `avatar` 字段
     - 显示 `role_name` 替代昵称（若设置了匿名角色名）
   - 若 `is_friend = false`: 陌生人只看到 `temp_id`（通过其他接口）

4. **返回过滤后的资料**

---

#### 2.1.3 `update_device(device_id, fields) -> UpdatedProfile`

#XXX

**逻辑步骤:**

1. **参数校验**
   - 检查 `device_id` 是否存在 → 不存在返回 4007
   - 校验各字段长度限制

2. **部分更新**
   ```sql
   UPDATE devices 
   SET nickname = COALESCE(?, nickname),
       avatar = COALESCE(?, avatar),
       tags = COALESCE(?, tags),
       profile = COALESCE(?, profile),
       is_anonymous = COALESCE(?, is_anonymous),
       role_name = COALESCE(?, role_name),
       updated_at = NOW()
   WHERE device_id = ?
   ```

3. **返回更新后的完整资料**

---

### 2.2 TempIdService

#### 2.2.1 `refresh_temp_id(device_id, current_temp_id) -> TempIdInfo`

**逻辑步骤:**

1. **验证设备存在**
   - 检查 `device_id` 是否存在于 `devices` 表 → 不存在返回 4007

2. **生成新 Temp ID**
   ```python
   # 伪代码
   timestamp = now()
   random_salt = generate_random(16)
   temp_id = hex(hash(device_id + SECRET_KEY + timestamp + random_salt))
   ```

3. **存储到 temp_ids 表**
   ```sql
   INSERT INTO temp_ids (temp_id, device_id, expires_at)
   VALUES (?, ?, NOW() + INTERVAL '5 minutes')
   ```

4. **处理旧 Temp ID**
   - 若传入 `current_temp_id`:
   ```sql
   UPDATE temp_ids 
   SET expires_at = NOW() + INTERVAL '5 minutes'
   WHERE temp_id = ? AND device_id = ?
   ```

5. **清理过期记录** (异步任务)
   ```sql
   DELETE FROM temp_ids WHERE expires_at < NOW() - INTERVAL '5 minutes'
   ```

6. **返回新 Temp ID**
   ```json
   {
     "temp_id": "a1b2c3d4e5f6...",
     "expires_at": "2026-03-14T11:00:00Z"
   }
   ```

---

#### 2.2.2 `resolve_temp_id(temp_id) -> device_id | None`

**逻辑步骤:**

1. **查询 temp_ids 表**
   ```sql
   SELECT device_id FROM temp_ids 
   WHERE temp_id = ? AND expires_at > NOW()
   ```

2. **返回结果**
   - 找到: 返回 `device_id`
   - 未找到或已过期: 返回 `None`（后续会过滤掉）

---

### 2.3 PresenceService

#### 2.3.1 `resolve_nearby_devices(device_id, scanned_devices) -> NearbyResult`

**逻辑步骤:**

1. **参数校验**
   - 校验 `device_id` 是否存在 → 不存在返回 4007

2. **解析 Temp IDs**
   ```python
   for item in scanned_devices:
       resolved_id = TempIdService.resolve_temp_id(item.temp_id)
       if resolved_id:
           item.device_id = resolved_id
           item.distance_estimate = rssi_to_distance(item.rssi)
   ```

3. **过滤屏蔽关系**
   ```sql
   SELECT target_id FROM blocks WHERE blocker_id = ?
   SELECT blocker_id FROM blocks WHERE target_id = ?
   ```
   - 移除被屏蔽和屏蔽请求者的设备

4. **获取设备资料** (批量查询)
   ```sql
   SELECT d.*, f.status as friendship_status
   FROM devices d
   LEFT JOIN friendships f ON 
       (f.user_id = ? AND f.friend_id = d.device_id) OR
       (f.friend_id = ? AND f.user_id = d.device_id)
   WHERE d.device_id IN (resolved_ids)
   ```

5. **应用隐私规则**
   - 对每个设备应用 `DeviceService` 的隐私过滤逻辑

6. **更新 Presence 表**
   ```sql
   INSERT INTO presence (user_id, nearby_user_id, last_seen_at)
   VALUES (?, ?, NOW())
   ON CONFLICT (user_id, nearby_user_id) 
   DO UPDATE SET last_seen_at = NOW()
   ```

7. **检测 Boost 条件**
   ```python
   boost_alerts = []
   for device in nearby_devices:
       if device.is_friend:
           # 检查上次 Boost 时间
           last_boost = get_last_boost(device_id, device.device_id)
           if not last_boost or (now() - last_boost) > 5 minutes:
               # 检查之前是否"不在附近"
               was_nearby = check_was_nearby_recently(device_id, device.device_id, minutes=5)
               if not was_nearby:
                   boost_alerts.append({
                       "device_id": device.device_id,
                       "nickname": device.nickname,
                       "distance_estimate": device.distance_estimate
                   })
                   record_boost_event(device_id, device.device_id)
                   
                   # WebSocket 推送
                   WebSocketManager.send_boost(device_id, device)
   ```

8. **返回结果**
   ```json
   {
     "nearby_devices": [...],
     "boost_alerts": [...]
   }
   ```

---

#### 2.3.2 `report_disconnect(device_id, left_device_id) -> DisconnectResult`

**逻辑步骤:**

1. **更新 Presence 表**
   ```sql
   UPDATE presence 
   SET last_disconnect_at = NOW()
   WHERE user_id = ? AND nearby_user_id = ?
   ```

2. **检查临时会话**
   ```sql
   SELECT session_id FROM sessions 
   WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
   AND is_temp = true AND expired_at IS NULL
   ```

3. **过期临时会话**
   - 若存在临时会话:
   ```sql
   UPDATE sessions SET expired_at = NOW() WHERE session_id = ?
   ```

4. **WebSocket 通知双方**
   ```python
   WebSocketManager.send_session_expired(device_id, left_device_id, session_id)
   WebSocketManager.send_session_expired(left_device_id, device_id, session_id)
   ```

5. **返回结果**
   ```json
   {
     "session_expired": true/false,
     "session_id": "uuid-or-null"
   }
   ```

---

### 2.4 MessagingService

#### 2.4.1 `send_message(sender_id, receiver_id, content, type) -> MessageResult`

**逻辑步骤:**

1. **参数校验**
   - 校验 `sender_id` 和 `receiver_id` 是否存在
   - 校验 `content` 长度 ≤ 1000 字符
   - 校验 `type` ∈ ['common', 'heartbeat']

2. **检查屏蔽关系**
   ```sql
   SELECT 1 FROM blocks 
   WHERE (blocker_id = ? AND target_id = ?) OR (blocker_id = ? AND target_id = ?)
   ```
   - 若存在 → 返回 4004

3. **判断好友关系**
   ```sql
   SELECT 1 FROM friendships 
   WHERE status = 'accepted' AND 
   ((user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?))
   ```

4. **非好友消息限制检查**
   - 若非好友:
     a. 检查是否存在有效临时会话
     b. 若无会话，创建临时会话
     c. 检查该会话中发送者消息数（对方未回复前）
     ```sql
     SELECT COUNT(*) FROM messages 
     WHERE session_id = ? AND sender_id = ? AND 
     NOT EXISTS (SELECT 1 FROM messages WHERE session_id = ? AND sender_id = ?)
     ```
     - 若 ≥ 2 条 → 返回 4001

5. **获取或创建会话**
   ```sql
   -- 查找现有会话
   SELECT session_id FROM sessions 
   WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
   
   -- 或创建新会话
   INSERT INTO sessions (session_id, user1_id, user2_id, is_temp)
   VALUES (uuid(), ?, ?, ?)
   ```

6. **存储消息**
   ```sql
   INSERT INTO messages (message_id, session_id, sender_id, receiver_id, content, type, status, created_at)
   VALUES (uuid(), ?, ?, ?, ?, ?, 'sent', NOW())
   ```

7. **WebSocket 推送**
   ```python
   # 推送给接收者
   WebSocketManager.send_message(receiver_id, {
       "type": "new_message",
       "payload": { ... }
   })
   
   # 确认给发送者
   WebSocketManager.send_message(sender_id, {
       "type": "message_sent",
       "payload": { ... }
   })
   ```

8. **返回结果**
   ```json
   {
     "message_id": "msg-uuid",
     "session_id": "session-uuid",
     "status": "sent",
     "created_at": "2026-03-14T10:53:00Z"
   }
   ```

---

#### 2.4.2 `get_message_history(session_id, device_id, before, limit) -> MessageList`

**逻辑步骤:**

1. **权限校验**
   ```sql
   SELECT 1 FROM sessions 
   WHERE session_id = ? AND (user1_id = ? OR user2_id = ?)
   ```
   - 无权限 → 返回 4008

2. **查询消息**
   ```sql
   SELECT * FROM messages 
   WHERE session_id = ? AND created_at < ?
   ORDER BY created_at DESC
   LIMIT ?
   ```

3. **返回分页结果**
   ```json
   {
     "session_id": "session-uuid",
     "messages": [...],
     "has_more": true/false
   }
   ```

---

#### 2.4.3 `mark_messages_read(device_id, message_ids) -> int`

**逻辑步骤:**

1. **验证消息归属**
   ```sql
   UPDATE messages 
   SET status = 'read', read_at = NOW()
   WHERE message_id IN (?) 
   AND receiver_id = ?  -- 确保是接收者在标记
   AND status != 'read'
   RETURNING sender_id, message_id
   ```

2. **通知发送者已读**
   ```python
   for sender_id, msg_id in updated:
       WebSocketManager.send_message(sender_id, {
           "type": "messages_read",
           "payload": {
               "message_ids": [msg_id],
               "reader_id": device_id,
               "read_at": "2026-03-14T10:55:00Z"
           }
       })
   ```

3. **返回更新数量**

---

### 2.5 RelationService

#### 2.5.1 `get_friends_list(device_id) -> FriendList`

**逻辑步骤:**

1. **查询好友关系**
   ```sql
   SELECT 
       CASE WHEN user_id = ? THEN friend_id ELSE user_id END as friend_id,
       status, created_at
   FROM friendships 
   WHERE (user_id = ? OR friend_id = ?) AND status = 'accepted'
   ```

2. **获取好友资料** (批量)
   ```sql
   SELECT * FROM devices WHERE device_id IN (friend_ids)
   ```

3. **获取最后聊天时间**
   ```sql
   SELECT MAX(created_at) as last_chat_at 
   FROM messages 
   WHERE session_id IN (
       SELECT session_id FROM sessions 
       WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
   )
   ```

4. **按最后聊天时间排序返回**

---

#### 2.5.2 `send_friend_request(sender_id, receiver_id, message) -> RequestResult`

**逻辑步骤:**

1. **检查屏蔽**
   ```sql
   SELECT 1 FROM blocks 
   WHERE (blocker_id = ? AND target_id = ?) OR (blocker_id = ? AND target_id = ?)
   ```
   - 存在 → 返回 4004

2. **检查冷却期** (24小时)
   ```sql
   SELECT updated_at FROM friendships 
   WHERE user_id = ? AND friend_id = ? AND status = 'rejected'
   ORDER BY updated_at DESC LIMIT 1
   ```
   - 若 `updated_at` 在 24h 内 → 返回 4005

3. **检查重复申请**
   ```sql
   SELECT 1 FROM friendships 
   WHERE user_id = ? AND friend_id = ? AND status = 'pending'
   ```
   - 存在 → 返回 4009

4. **检查是否已是好友**
   ```sql
   SELECT 1 FROM friendships 
   WHERE status = 'accepted' AND 
   ((user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?))
   ```
   - 存在 → 返回 4009（或视为成功）

5. **创建申请记录**
   ```sql
   INSERT INTO friendships (request_id, user_id, friend_id, status, message, created_at)
   VALUES (uuid(), ?, ?, 'pending', ?, NOW())
   ```

6. **WebSocket 推送**
   ```python
   WebSocketManager.send_message(receiver_id, {
       "type": "friend_request",
       "payload": { ... }
   })
   ```

7. **返回结果**

---

#### 2.5.3 `respond_friend_request(request_id, device_id, action) -> ResponseResult`

**逻辑步骤:**

1. **验证请求存在且属于当前用户**
   ```sql
   SELECT * FROM friendships 
   WHERE request_id = ? AND friend_id = ? AND status = 'pending'
   ```
   - 不存在 → 返回 4008

2. **分支处理**

   **Accept:**
   ```sql
   UPDATE friendships SET status = 'accepted', updated_at = NOW() WHERE request_id = ?
   ```
   - 查找或创建永久会话
   ```sql
   SELECT session_id FROM sessions 
   WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
   
   -- 若存在临时会话，升级为永久
   UPDATE sessions SET is_temp = false WHERE session_id = ?
   
   -- 或创建新永久会话
   INSERT INTO sessions (session_id, user1_id, user2_id, is_temp)
   VALUES (uuid(), ?, ?, false)
   ```

   **Reject:**
   ```sql
   UPDATE friendships SET status = 'rejected', updated_at = NOW() WHERE request_id = ?
   ```

3. **WebSocket 通知申请方**
   ```python
   WebSocketManager.send_message(sender_id, {
       "type": "friend_response",
       "payload": { ... }
   })
   ```

4. **返回结果**

---

#### 2.5.4 `delete_friend(device_id, friend_device_id)`

**逻辑步骤:**

1. **删除好友关系**
   ```sql
   DELETE FROM friendships 
   WHERE ((user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?))
   AND status = 'accepted'
   ```

2. **可选: 降级会话为临时**
   ```sql
   UPDATE sessions 
   SET is_temp = true 
   WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
   ```

---

#### 2.5.5 `block_user(device_id, target_id)`


**逻辑步骤:**

1. **检查是否已是好友，若是则删除**
   ```sql
   DELETE FROM friendships 
   WHERE ((user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?))
   ```

2. **添加屏蔽记录**
   ```sql
   INSERT INTO blocks (blocker_id, target_id, created_at)
   VALUES (?, ?, NOW())
   ON CONFLICT DO NOTHING
   ```

3. **清理 presence 记录** (互不可见)
   ```sql
   DELETE FROM presence 
   WHERE (user_id = ? AND nearby_user_id = ?) OR (user_id = ? AND nearby_user_id = ?)
   ```

---

#### 2.5.6 `unblock_user(device_id, target_id)`

**逻辑步骤:**

1. **删除屏蔽记录**
   ```sql
   DELETE FROM blocks WHERE blocker_id = ? AND target_id = ?
   ```

---

### 2.6 WebSocketManager

#### 2.6.1 `connect(device_id, websocket)`

**逻辑步骤:**

1. **存储连接**
   ```python
   connections[device_id] = websocket
   ```

2. **发送连接确认**
   ```json
   {
     "type": "connected",
     "payload": {
       "device_id": "device_id",
       "server_time": "2026-03-14T10:53:00Z"
     }
   }
   ```

> **注意**: Server 不维护 "在线状态"，仅管理 WebSocket 连接

---

#### 2.6.2 `disconnect(device_id)`

**逻辑步骤:**

1. **移除连接**
   ```python
   del connections[device_id]
   ```

2. **注意**: 不更新任何 "在线状态" 字段

---

#### 2.6.3 `send_message(device_id, message) -> bool`

**逻辑步骤:**

1. **获取连接**
   ```python
   ws = connections.get(device_id)
   ```

2. **发送消息** (不判断连接是否存在，直接尝试发送)
   ```python
   if ws:
       await ws.send_json(message)
       return true
   return false
   ```

> **V2 变更**: 始终尝试推送，不判断 "在线状态"

---

#### 2.6.4 `handle_client_message(device_id, data)`

**处理客户端消息:**

| action | 处理逻辑 |
|--------|----------|
| `send_message` | 调用 `MessagingService.send_message` |
| `mark_read` | 调用 `MessagingService.mark_messages_read` |
| `ping` | 返回 `{"type": "pong"}` |

---

## 3. 数据模型

### 3.1 表结构

```sql
-- 设备表
CREATE TABLE devices (
    device_id UUID PRIMARY KEY,
    nickname VARCHAR(50) NOT NULL,
    avatar VARCHAR(500),
    tags TEXT[],
    profile VARCHAR(200),
    is_anonymous BOOLEAN DEFAULT false,
    role_name VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- 临时 ID 表
CREATE TABLE temp_ids (
    temp_id CHAR(32) PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(device_id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    INDEX idx_device_id (device_id),
    INDEX idx_expires_at (expires_at)
);

-- 附近关系表 (仅记录最后发现时间，无在线状态)
CREATE TABLE presence (
    user_id UUID NOT NULL REFERENCES devices(device_id),
    nearby_user_id UUID NOT NULL REFERENCES devices(device_id),
    last_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_disconnect_at TIMESTAMP,
    last_boost_at TIMESTAMP,
    PRIMARY KEY (user_id, nearby_user_id)
);

-- 会话表
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY,
    user1_id UUID NOT NULL REFERENCES devices(device_id),
    user2_id UUID NOT NULL REFERENCES devices(device_id),
    is_temp BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expired_at TIMESTAMP,
    UNIQUE (user1_id, user2_id)
);

-- 消息表
CREATE TABLE messages (
    message_id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(session_id),
    sender_id UUID NOT NULL REFERENCES devices(device_id),
    receiver_id UUID NOT NULL REFERENCES devices(device_id),
    content VARCHAR(1000) NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'common',
    status VARCHAR(20) NOT NULL DEFAULT 'sent', -- sent, read
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    read_at TIMESTAMP,
    INDEX idx_session_created (session_id, created_at)
);

-- 好友关系表
CREATE TABLE friendships (
    request_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES devices(device_id),
    friend_id UUID NOT NULL REFERENCES devices(device_id),
    status VARCHAR(20) NOT NULL, -- pending, accepted, rejected
    message VARCHAR(200),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    UNIQUE (user_id, friend_id)
);

-- 屏蔽表
CREATE TABLE blocks (
    blocker_id UUID NOT NULL REFERENCES devices(device_id),
    target_id UUID NOT NULL REFERENCES devices(device_id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (blocker_id, target_id)
);
```

---

## 4. 关键流程时序

### 4.1 设备初始化流程

```
┌─────────┐                    ┌─────────────┐
│ Client  │                    │   Server    │
└────┬────┘                    └──────┬──────┘
     │                                │
     │  POST /device/init             │
     │  {device_id, nickname...}      │
     │ ─────────────────────────────> │
     │                                │
     │  {code: 0, is_new: true, ...}  │
     │ <───────────────────────────── │
     │                                │
```

---

### 4.2 附近发现 + Boost 流程

```
┌─────────┐                    ┌─────────────┐              ┌─────────┐
│ User A  │                    │   Server    │              │ User B  │
└────┬────┘                    └──────┬──────┘              └────┬────┘
     │                                │                          │
     │  POST /temp-id/refresh         │                          │
     │ ─────────────────────────────> │                          │
     │  {temp_id: "abc123"}           │                          │
     │ <───────────────────────────── │                          │
     │                                │                          │
     │  [BLE广播: temp_id="abc123"]   │                          │
     │ ═══════════════════════════════════════════════════════> │
     │                                │                          │
     │                                │      POST /presence/resolve
     │                                │  {scanned_devices: [{"temp_id": "abc123"}]}
     │                                │ <───────────────────────── │
     │                                │                          │
     │                                │  检测: B和A是好友?         │
     │                                │  检测: 上次Boost > 5min?   │
     │                                │  是 → 记录boost_alerts     │
     │                                │                          │
     │     WS: boost {"device_id": B} │                          │
     │ <═══════════════════════════════════════════════════════ │
     │                                │                          │
     │                                │  {nearby_devices: [A], boost_alerts: [A]}
     │                                │ ─────────────────────────> │
     │                                │                          │
```

---

### 4.3 临时聊天 + 成为好友流程

```
┌─────────┐                    ┌─────────────┐              ┌─────────┐
│ User A  │                    │   Server    │              │ User B  │
└────┬────┘                    └──────┬──────┘              └────┬────┘
     │                                │                          │
     │  WS: send_message → B          │                          │
     │ ─────────────────────────────> │                          │
     │                                │                          │
     │                                │  检查: 非好友, 检查消息限制 │
     │                                │  创建临时会话              │
     │                                │                          │
     │     WS: message_sent           │                          │
     │ <───────────────────────────── │                          │
     │                                │                          │
     │                                │     WS: new_message        │
     │                                │ ─────────────────────────> │
     │                                │                          │
     │  [A 继续发送第2条消息]          │                          │
     │  [A 尝试发送第3条消息]          │                          │
     │ ─────────────────────────────> │                          │
     │                                │  检查: 已达2条上限         │
     │     WS: error {code: 4001}     │                          │
     │ <───────────────────────────── │                          │
     │                                │                          │
     │  发送好友申请                    │                          │
     │  POST /friends/request         │                          │
     │ ─────────────────────────────> │                          │
     │                                │     WS: friend_request     │
     │                                │ ─────────────────────────> │
     │                                │                          │
     │                                │      PUT /friends/{id}     │
     │                                │      {action: "accept"}    │
     │                                │ <───────────────────────── │
     │                                │                          │
     │                                │  升级临时会话为永久         │
     │                                │                          │
     │     WS: friend_response        │                          │
     │ <───────────────────────────── │                          │
     │                                │                          │
     │  现在可以无限制聊天              │                          │
     │                                │                          │
```

---

### 4.4 离开范围会话过期流程

```
┌─────────┐                    ┌─────────────┐              ┌─────────┐
│ User A  │                    │   Server    │              │ User B  │
└────┬────┘                    └──────┬──────┘              └────┬────┘
     │                                │                          │
     │  [BLE 连续60秒未扫描到B]        │                          │
     │                                │                          │
     │  POST /presence/disconnect     │                          │
     │  {left_device_id: B}           │                          │
     │ ─────────────────────────────> │                          │
     │                                │                          │
     │                                │  更新 presence 表         │
     │                                │  过期临时会话             │
     │                                │                          │
     │     WS: session_expired        │                          │
     │ <───────────────────────────── │                          │
     │                                │     WS: session_expired    │
     │                                │ ─────────────────────────> │
     │                                │                          │
     │  [UI显示: 会话已过期]           │                          │
     │                                │                          │
```

---

## 附录: 工具函数

### RSSI 转距离估算

```python
def rssi_to_distance(rssi: int) -> float:
    """
    基于 RSSI 估算距离（米）
    简化模型: distance = 10 ^ ((tx_power - rssi) / (10 * n))
    tx_power: 发射功率 (通常 -59 dBm 在 1 米处)
    n: 路径损耗指数 (通常 2.0)
    """
    tx_power = -59  # 1米处的参考RSSI
    n = 2.0  # 自由空间路径损耗
    
    distance = 10 ** ((tx_power - rssi) / (10 * n))
    return round(distance, 1)
```

### Temp ID 生成

```python
import hashlib
import secrets
import time

def generate_temp_id(device_id: str, secret_key: str) -> str:
    """生成临时 ID"""
    timestamp = str(int(time.time()))
    random_salt = secrets.token_hex(8)
    
    data = f"{device_id}:{secret_key}:{timestamp}:{random_salt}"
    temp_id = hashlib.sha256(data.encode()).hexdigest()[:32]
    
    return temp_id
```
