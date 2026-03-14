# 塞纸条 (NotePassing) 服务器设计文档

> 设计理念：一个设备即一个用户，无需登录认证

---

## 1. 数据模型

### 1.1 用户/设备表 (devices)

| 字段 | 类型 | 说明 |
|------|------|------|
| device_id | VARCHAR(32) PRIMARY KEY | 设备唯一标识（如 Android ID 或 UUID） |
| nickname | VARCHAR(50) | 昵称 |
| avatar | TEXT | 头像 URL |
| tags | JSONB | 标签列表，如 ["摄影", "ACG"] |
| profile | TEXT | 简短简介 |
| is_anonymous | BOOLEAN | 是否为匿名模式 |
| role_name | VARCHAR(50) | 自定义角色名（匿名模式下显示） |
| created_at | TIMESTAMP | 首次使用时间 |
| updated_at | TIMESTAMP | 更新时间 |

> 设备首次使用时自动创建记录，无需注册流程

### 1.2 好友关系表 (friendships)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PRIMARY KEY | 关系ID |
| device_a_id | VARCHAR(32) FK | 设备A |
| device_b_id | VARCHAR(32) FK | 设备B |
| status | ENUM | 状态: pending, accepted, blocked |
| created_at | TIMESTAMP | 创建时间 |
| accepted_at | TIMESTAMP | 接受时间 |

**约束**: `device_a_id < device_b_id` 避免重复

### 1.3 消息表 (messages)

| 字段 | 类型 | 说明 |
|------|------|------|
| message_id | UUID PRIMARY KEY | 消息ID |
| sender_id | VARCHAR(32) FK | 发送者设备ID |
| receiver_id | VARCHAR(32) FK | 接收者设备ID |
| session_id | UUID FK | 会话ID |
| content | TEXT | 消息内容 |
| type | ENUM | 类型: text, friend_request, heartbeat |
| status | ENUM | 状态: sending, sent, delivered, read |
| created_at | TIMESTAMP | 创建时间 |
| read_at | TIMESTAMP | 已读时间 |

### 1.4 会话表 (sessions)

| 字段 | 类型 | 说明 |
|------|------|------|
| session_id | UUID PRIMARY KEY | 会话ID |
| device_a_id | VARCHAR(32) FK | 设备A |
| device_b_id | VARCHAR(32) FK | 设备B |
| is_temp | BOOLEAN | 是否为临时会话（非好友） |
| last_message_at | TIMESTAMP | 最后消息时间 |
| expires_at | TIMESTAMP | 临时会话过期时间（蓝牙断开1分钟后） |
| created_at | TIMESTAMP | 创建时间 |

**索引**: `(device_a_id, device_b_id)`, `expires_at`

### 1.5 临时 ID 表 (temp_ids)

| 字段 | 类型 | 说明 |
|------|------|------|
| temp_id | VARCHAR(32) PRIMARY KEY | 临时加密ID |
| device_id | VARCHAR(32) FK | 对应设备ID |
| rssi | INT | 信号强度（可选，服务器记录） |
| expires_at | TIMESTAMP | 过期时间（建议5-10分钟轮换） |
| created_at | TIMESTAMP | 创建时间 |

**索引**: `device_id`, `expires_at`

### 1.6 附近状态表 (presence)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PRIMARY KEY | 记录ID |
| device_id | VARCHAR(32) FK | 设备ID |
| nearby_device_id | VARCHAR(32) FK | 附近设备ID |
| rssi | INT | 蓝牙信号强度 |
| distance_estimate | FLOAT | 估算距离（米） |
| first_seen_at | TIMESTAMP | 首次发现时间 |
| last_seen_at | TIMESTAMP | 最后发现时间 |
| is_online | BOOLEAN | 是否仍在范围内 |

**索引**: `(device_id, nearby_device_id)`, `last_seen_at`

---

## 2. 核心服务模块

### 2.1 Device Service（设备服务）

**功能**:
- 设备首次使用自动创建设备记录
- 获取/更新设备资料（昵称、头像、标签等）
- 切换匿名/自定义角色

**接口**:
- `POST /device/init` - 设备初始化（首次使用调用）
  ```http
  POST /device/init
  
  请求体:
  {
      "device_id": "android_device_uuid",
      "nickname": "小明",
      "tags": ["摄影"],
      "profile": "喜欢拍照"
  }
  
  响应: 201 Created
  {
      "device_id": "android_device_uuid",
      "nickname": "小明",
      "created_at": "2026-03-14T10:53:00Z"
  }
  ```

- `GET /device/:device_id` - 获取设备资料
- `PUT /device/:device_id` - 更新设备资料
- `POST /device/:device_id/role` - 切换角色模式

### 2.2 Presence Service（附近关系服务）

**功能**:
- 解析临时 ID 获取设备信息
- 管理附近设备列表
- 距离估算
- 好友接近检测（Boost）

**核心逻辑**:

```
resolveNearby(token_list, my_device_id):
    1. 查询 temp_ids 表获取真实设备ID
    2. 过滤已屏蔽设备
    3. 根据好友状态返回不同级别信息：
       - 陌生人: 仅 nickname, tags, profile
       - 好友: 额外显示完整资料 + Boost 标记
    4. 更新 presence 表
    5. 检查是否需要触发 Boost（好友重新进入范围）
```

**接口**:
- `POST /presence/resolve` - 解析附近临时ID列表
- `GET /presence/nearby?device_id=xxx` - 获取当前附近设备
- `DELETE /presence/:device_id` - 移除某附近设备记录

### 2.3 Messaging Service（消息服务）

**功能**:
- 发送/接收消息
- 好友申请处理
- Heartbeat 心跳
- 临时聊天限制（未好友最多2条）

**消息类型**:

| 类型 | 说明 | 处理逻辑 |
|------|------|----------|
| `common` | 普通消息 | 检查会话状态，好友无限制，非好友限制2条 |
| `friend_request` | 好友申请 | 直接转发，创建 pending 好友关系 |
| `friend_response` | 好友回应 | yes: 更新 friendships 状态，升级为好友会话；no: 通知拒绝 |
| `heartbeat` | 心跳 | 直接转发，用于维持连接 |

**接口**:
- WebSocket `/ws?device_id=xxx` - 实时消息（通过 URL 参数传递设备ID）
- `GET /messages/:session_id` - 获取历史消息
- `POST /messages/read` - 标记已读

### 2.4 Relation Service（好友关系服务）

**功能**:
- 好友列表管理
- 好友申请/接受/拒绝
- 屏蔽设备

**接口**:
- `GET /friends?device_id=xxx` - 好友列表
- `POST /friends/request` - 发送好友申请
- `PUT /friends/:id/accept` - 接受好友
- `PUT /friends/:id/reject` - 拒绝好友
- `DELETE /friends/:id` - 删除好友

---

## 3. 临时 ID 机制

### 3.1 生成规则

```
temp_id = hash(device_id + secret_key + timestamp + random_salt)
```

**参数**:
- 长度: 32字符十六进制
- 轮换周期: 5-10分钟
- 过期保留: 额外5分钟缓冲（避免切换时找不到）

### 3.2 客户端流程

1. 客户端定期从服务器获取新的 temp_id
2. 通过 BLE 广播该 temp_id
3. 其他设备扫描到后上传服务器解析

### 3.3 服务器接口

```http
POST /temp-id/refresh

请求体:
{
    "device_id": "my_device_uuid",
    "current_temp_id": "xxx"  // 可选，用于清理旧ID
}

响应:
{
    "temp_id": "new_temp_id",
    "expires_at": "2026-03-14T11:00:00Z"
}
```

---

## 4. 临时聊天机制

### 4.1 会话创建

当陌生人首次发消息时:
1. 创建临时会话 (`is_temp = true`)
2. 设置 `expires_at` 为当前时间 + 1分钟（后续根据蓝牙状态更新）

### 4.2 消息限制

```python
def can_send_message(sender_id, receiver_id):
    if is_friend(sender_id, receiver_id):
        return True
    
    count = messages.count(
        sender_id=sender_id,
        receiver_id=receiver_id,
        session__is_temp=True,
        created_at > session.created_at
    )
    return count < 2
```

### 4.3 蓝牙断开检测

客户端行为:
- 每 5-10 秒扫描一次附近设备
- 若某设备连续 6 次（约1分钟）未扫描到，视为超出范围
- 通知服务器关闭临时会话

服务器行为:
- 收到断开通知后，标记会话为 `expired`
- 向双方发送会话结束通知
- 保留消息记录但禁止新消息

---

## 5. Boost 功能

### 5.1 触发条件

当满足以下条件时触发 Boost:
1. 双方是好友关系
2. 对方重新进入蓝牙范围（从不在附近变为在附近）
3. 距离上次 Boost 间隔 > 5分钟（防重复触发）

### 5.2 推送方式

```http
WebSocket 推送:
{
    "type": "boost",
    "payload": {
        "device_id": "friend_device_id",
        "nickname": "好友昵称",
        "distance": 2.5,
        "timestamp": "2026-03-14T10:53:00Z"
    }
}
```

客户端响应: 震动 + UI 高亮显示

---

## 6. API 详细设计

### 6.1 REST API

#### 设备初始化

```http
POST /api/v1/device/init

请求体:
{
    "device_id": "android_uuid_from_settings",
    "nickname": "默认昵称",
    "tags": [],
    "profile": ""
}

响应: 201 Created（新设备）或 200 OK（已存在）
{
    "device_id": "android_uuid",
    "nickname": "默认昵称",
    "is_new": true
}
```

#### 解析附近设备

```http
POST /api/v1/presence/resolve

请求体:
{
    "device_id": "my_device_uuid",
    "temp_ids": [
        { "temp_id": "abc123...", "rssi": -65 },
        { "temp_id": "def456...", "rssi": -80 }
    ]
}

响应:
{
    "devices": [
        {
            "device_id": "uuid",
            "temp_id": "abc123...",
            "nickname": "小明",
            "tags": ["摄影", "旅行"],
            "profile": "喜欢拍照的程序员",
            "distance_estimate": 2.5,
            "is_friend": false,
            "is_anonymous": false
        }
    ],
    "boost_triggered": [
        { "device_id": "friend_device_id", "nickname": "好友" }
    ]
}
```

#### 发送消息（REST 备用）

```http
POST /api/v1/messages

请求体:
{
    "sender_id": "my_device_uuid",
    "receiver_id": "target_device_uuid",
    "content": "你好",
    "type": "common"
}

响应:
{
    "message_id": "uuid",
    "status": "sent",
    "created_at": "2026-03-14T10:53:00Z"
}

错误:
400 - 临时聊天已达2条上限
403 - 已被对方屏蔽
```

#### 获取好友列表

```http
GET /api/v1/friends?device_id=my_device_uuid

响应:
{
    "friends": [
        {
            "device_id": "friend_uuid",
            "nickname": "好友",
            "avatar": "url",
            "last_chat_at": "2026-03-14T10:00:00Z"
        }
    ]
}
```

### 6.2 WebSocket 协议

连接: `wss://api.notepassing.app/ws?device_id=<device_id>`

> 通过 URL 参数传递 device_id，无需认证

**客户端发送**:

```json
// 发送消息
{
    "action": "send_message",
    "payload": {
        "receiver_id": "target_device_uuid",
        "content": "你好",
        "type": "common"
    }
}

// 心跳保活
{
    "action": "ping"
}

// 已读确认
{
    "action": "mark_read",
    "payload": {
        "message_ids": ["uuid1", "uuid2"]
    }
}
```

**服务器推送**:

```json
// 新消息
{
    "type": "new_message",
    "payload": {
        "message_id": "uuid",
        "sender_id": "device_uuid",
        "content": "你好",
        "type": "common",
        "created_at": "2026-03-14T10:53:00Z"
    }
}

// 好友申请
{
    "type": "friend_request",
    "payload": {
        "request_id": "uuid",
        "sender": { "device_id": "uuid", "nickname": "小明" },
        "message": "想加你为好友"
    }
}

// Boost 提示
{
    "type": "boost",
    "payload": {
        "device_id": "friend_device_id",
        "nickname": "好友",
        "distance": 2.5
    }
}

// 临时会话结束
{
    "type": "session_expired",
    "payload": {
        "session_id": "uuid",
        "reason": "out_of_range"
    }
}

// 心跳响应
{
    "type": "pong"
}
```

---

## 7. 安全与隐私

### 7.1 隐私控制

| 信息类型 | 陌生人可见 | 好友可见 |
|----------|-----------|----------|
| nickname | ✓ | ✓ |
| tags | ✓ | ✓ |
| profile | ✓ | ✓ |
| avatar | 匿名模式下隐藏 | ✓ |
| 真实 device_id | ✗（仅显示 temp_id） | ✓ |
| friend_list | ✗ | ✓ |

### 7.2 防骚扰

- 陌生人消息限制: 未回复前最多2条
- 好友申请冷却: 被拒绝后24小时内不能重复申请
- 屏蔽功能: 屏蔽后双方无法看到对方

### 7.3 风险提示

> ⚠️ 无认证模式下，设备ID可能被伪造。建议：
> 1. 客户端生成随机 UUID 作为 device_id（不要直接用 Android ID）
> 2. 或使用设备指纹 + 签名验证
> 3. 敏感操作（如修改资料）可添加简单验证码

---

## 8. 数据库索引建议

```sql
-- 加速附近设备查询
CREATE INDEX idx_presence_device_seen ON presence(device_id, is_online, last_seen_at);

-- 加速临时ID解析
CREATE INDEX idx_temp_id_expires ON temp_ids(temp_id, expires_at);

-- 加速会话查询
CREATE INDEX idx_session_devices ON sessions(device_a_id, device_b_id);
CREATE INDEX idx_session_temp_expires ON sessions(is_temp, expires_at);

-- 加速消息查询
CREATE INDEX idx_messages_session ON messages(session_id, created_at DESC);
CREATE INDEX idx_messages_receiver ON messages(receiver_id, status, created_at);

-- 加速好友查询
CREATE INDEX idx_friendships_device ON friendships(device_a_id, status);
CREATE INDEX idx_friendships_pair ON friendships(device_a_id, device_b_id);
```

---

## 9. 技术栈

- **后端框架**: Python + FastAPI / Node.js + Express
- **数据库**: PostgreSQL (主) + Redis (缓存/在线状态)
- **实时通信**: WebSocket (Socket.io / 原生 WS)
- **部署**: Docker + Cloud Run / AWS Lambda

---

## 10. 错误码定义

| 错误码 | 说明 |
|--------|------|
| 4001 | 临时聊天消息已达上限(2条) |
| 4002 | 临时会话已过期 |
| 4003 | 不在蓝牙范围内 |
| 4004 | 已被对方屏蔽 |
| 4005 | 好友申请冷却中 |
| 4006 | 无效的临时ID |
| 4007 | 设备未初始化 |
| 5001 | 设备ID格式错误 |
| 5002 | 设备不在线 |
