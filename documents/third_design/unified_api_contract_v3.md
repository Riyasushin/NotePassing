# NotePassing 统一接口契约 V3 (Unified API Contract V3)

> 本文档为 `documents/third_design/` 当前唯一接口定义。  
> 若与 `second_design/` 或旧版 README 冲突，以本文为准。  
> **更新日期**: 2026-03-14  
> **V3 收口项**:
> - block 路径统一为 `/api/v1/block`
> - 新增 `GET /api/v1/messages/sync`
> - `GET /api/v1/messages/{session_id}` 支持 `after` 增量同步
> - 保留 V2 的 `chatable` / `heartbeat` / `temp-session` 规则

---

## 0. 通用约定

### 0.1 基础信息

| 项目 | 值 |
|---|---|
| 基础路径 | `/api/v1` |
| 协议 | HTTPS（REST） / WSS（WebSocket） |
| 数据格式 | JSON（`Content-Type: application/json`） |
| 编码 | UTF-8 |
| 时间格式 | ISO 8601（`2026-03-14T10:53:00Z`） |
| ID 格式 | `device_id`: 客户端生成的 UUID v4（32位十六进制字符串）；其余 ID 由服务器生成 UUID |

### 0.2 认证方式

无认证。设备 ID 即身份标识（`device_id` 通过请求体或查询参数传递）。

> ⚠️ 出于安全考虑，客户端应在首次启动时生成随机 UUID 并持久化，不要使用 Android ID。

### 0.3 统一响应格式

**成功响应：**

```json
{
    "code": 0,
    "message": "ok",
    "data": { ... }
}
```

**错误响应：**

```json
{
    "code": 4001,
    "message": "临时聊天消息已达上限",
    "data": null
}
```

### 0.4 错误码定义

| 错误码 | 含义 | 触发场景 |
|--------|------|----------|
| 0 | 成功 | — |
| 4001 | 临时聊天消息已达上限 | 非好友发送超过 2 条消息 |
| 4002 | 临时会话已过期 | 蓝牙断开超过 1 分钟后继续发消息 |
| 4003 | 不在蓝牙范围内 | 尝试向非附近用户发起临时聊天 |
| 4004 | 已被对方屏蔽 | 向屏蔽自己的用户发消息/好友申请 |
| 4005 | 好友申请冷却中 | 被拒绝后 24h 内重复申请 |
| 4006 | 无效的临时 ID | temp_id 已过期或不存在 |
| 4007 | 设备未初始化 | 未调用 init 就使用其他接口 |
| 4008 | 好友关系不存在 | 操作不存在的好友关系 |
| 4009 | 重复操作 | 重复发送好友申请等 |
| 5001 | 参数格式错误 | device_id 格式错误、必填字段缺失等 |
| 5002 | 服务器内部错误 | 服务端未预期异常 |

### 0.5 隐私可见性规则

| 字段 | 陌生人可见 | 好友可见 |
|------|-----------|----------|
| nickname | 匿名模式下显示 `不愿透露姓名的ta` | ✓ |
| tags | 匿名模式下隐藏 | ✓ |
| profile | 匿名模式下隐藏 | ✓ |
| avatar | 匿名模式下隐藏 | ✓ |
| device_id | ✗（陌生人只看到 temp_id） | ✓ |
| is_anonymous | ✓ | ✓ |
| role_name | 匿名模式下隐藏 | ✓ |

---

## 1. Device Service（设备服务）

### 1.1 设备初始化

客户端首次启动时调用，创建或恢复设备记录。

```
POST /api/v1/device/init
```

**请求体：**

```json
{
    "device_id": "550e8400-e29b-41d4-a716-446655440000",
    "nickname": "默认昵称",
    "tags": [],
    "profile": ""
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 客户端生成的 UUID v4 |
| nickname | string | ✓ | 昵称（最长 50 字符） |
| tags | string[] | ✗ | 标签列表，默认空数组 |
| profile | string | ✗ | 简介（最长 200 字符） |

> **注意**: 头像、匿名设置、角色名等通过 `PUT /api/v1/device/{device_id}` 更新，不在初始化时设置。

**响应：**

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

| 字段 | 说明 |
|------|------|
| is_new | `true` = 新设备首次注册；`false` = 已有设备恢复 |

**Local App 行为：** 启动时检查本地是否已有 device_id，若无则生成 UUID 并调用此接口；若有则仍调用（服务器返回 `is_new: false` 即恢复）。

**Server 行为：** 若 device_id 不存在则创建记录（201）；若已存在则返回现有记录（200）。统一包装在 `code: 0` 中。

---

### 1.2 获取设备资料

```
GET /api/v1/device/{device_id}
```

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| device_id | string | 目标设备 ID |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| requester_id | string | ✓ | 请求者的 device_id（用于隐私过滤） |

**响应：**

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

**Server 行为：** 根据 requester_id 与目标的关系，按隐私规则过滤字段。若目标为匿名模式且 requester 不是好友，则返回固定昵称 `不愿透露姓名的ta`，并隐藏 avatar / tags / profile / role_name。

> **注意**: Server 不判断设备是否"在线"，收到请求即返回资料。

---

### 1.3 更新设备资料

```
PUT /api/v1/device/{device_id}
```

**请求体（部分更新，只传需要改的字段）：**

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

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| nickname | string | ✗ | 最长 50 字符 |
| avatar | string | ✗ | 头像 URL |
| tags | string[] | ✗ | 标签列表 |
| profile | string | ✗ | 最长 200 字符 |
| is_anonymous | boolean | ✗ | 是否匿名模式 |
| role_name | string | ✗ | 匿名模式下的角色名（最长 50 字符） |

**响应：**

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

---

### 1.4 上传头像

```
POST /api/v1/device/{device_id}/avatar
```

**请求方式：** `multipart/form-data`

**表单字段：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | binary | ✓ | 图片文件，当前用于头像上传 |

**响应：**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "avatar_url": "http://39.102.97.149:8000/uploads/avatars/550e8400_avatar.jpg",
        "updated_at": "2026-03-15T10:30:00Z"
    }
}
```

**Server 行为：** 将图片保存到本地 `uploads/avatars/` 目录，生成可直接访问的 URL，并自动写回 `devices.avatar`。如果同一设备之前已有本地上传头像，则替换旧文件。

**Android 行为：** 设置页通过系统相册选图后，直接调用该接口；成功后把返回的 `avatar_url` 自动写回本地设置并用于头像显示。

---

## 2. Temp ID Service（临时 ID 服务）

### 2.1 刷新临时 ID

客户端定期调用以获取新的 BLE 广播 ID（建议每 5 分钟轮换一次）。

```
POST /api/v1/temp-id/refresh
```

**请求体：**

```json
{
    "device_id": "my_device_uuid",
    "current_temp_id": "old_temp_id_hex"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 自身设备 ID |
| current_temp_id | string | ✗ | 当前使用的 temp_id，传入后服务器标记为即将过期 |

**响应：**

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

| 字段 | 说明 |
|------|------|
| temp_id | 32 字符十六进制字符串，用于 BLE 广播 |
| expires_at | 过期时间，客户端应在此之前重新刷新 |

**Local App 行为：**
1. 启动后立即调用获取首个 temp_id
2. 使用 BLE 广播该 temp_id
3. 在 `expires_at` 前 30 秒自动调用刷新
4. 旧 temp_id 在服务端额外保留 5 分钟缓冲期

**Server 行为：**
1. 生成规则：`temp_id = hex(hash(device_id + secret_key + timestamp + random_salt))`
2. 存入 temp_ids 表，关联 device_id
3. 若传入 `current_temp_id`，将其过期时间缩短至 5 分钟后

---

## 3. Presence Service（附近关系服务）

### 3.1 解析附近设备

客户端将 BLE 扫描到的 temp_id 列表上传，服务器解析为用户名片。

```
POST /api/v1/presence/resolve
```

**请求体：**

```json
{
    "device_id": "my_device_uuid",
    "scanned_devices": [
        { "temp_id": "abc123def456...", "rssi": -65 },
        { "temp_id": "789xyz000111...", "rssi": -80 }
    ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 自身设备 ID |
| scanned_devices | array | ✓ | BLE 扫描结果列表 |
| scanned_devices[].temp_id | string | ✓ | 扫描到的临时 ID |
| scanned_devices[].rssi | int | ✓ | 蓝牙信号强度（dBm） |

**响应：**

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

| 字段 | 说明 |
|------|------|
| nearby_devices | 解析后的附近用户列表（已过滤屏蔽用户） |
| nearby_devices[].distance_estimate | 根据 RSSI 估算的距离（米） |
| nearby_devices[].is_friend | 是否为好友 |
| boost_alerts | 本次发现的好友（从"不在附近"变为"在附近"），触发 Boost |

**Local App 行为：**
1. 定期（每 5-10 秒）执行 BLE 扫描
2. 将扫描到的 temp_id + rssi 上传此接口
3. 用返回的 `nearby_devices` 更新本地 `chatable` 列表
4. 若 `boost_alerts` 非空，触发震动 + UI 高亮
5. 若某设备连续 6 次扫描（约 1 分钟）未出现，视为离开范围，调用 `presence/disconnect`

**Server 行为：**
1. 查询 temp_ids 表，将 temp_id 解析为 device_id
2. 过滤被屏蔽的设备
3. 根据好友关系和隐私规则返回不同级别信息
4. 更新 presence 表（记录谁在谁附近，仅更新 `last_seen_at`，不维护在线状态）
5. 检测好友 Boost 条件（好友从离开变为附近，且距上次 Boost ≥ 5 分钟）

> **重要**: Server 不判断设备是否"在线"，只记录最后发现时间。离线判断完全由客户端负责。

---

### 3.2 上报离开范围

客户端检测到某设备离开蓝牙范围后通知服务器。

```
POST /api/v1/presence/disconnect
```

**请求体：**

```json
{
    "device_id": "my_device_uuid",
    "left_device_id": "target_device_uuid"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 自身设备 ID |
| left_device_id | string | ✓ | 离开范围的设备 ID |

**响应：**

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

| 字段 | 说明 |
|------|------|
| session_expired | 是否有临时会话因此过期 |
| session_id | 过期的会话 ID（若有） |

**Local App 行为：** 某设备连续 ~1 分钟未被扫描到时调用此接口，并清理本地 `chatable` 列表中的该设备。

**Server 行为：**
1. 更新 presence 表，记录最后离线时间（**不设置 `is_online` 字段**）
2. 若存在临时会话（`is_temp = true`），标记为过期
3. 通过 WebSocket 向双方推送 `session_expired` 事件

---

## 4. Messaging Service（消息服务）

### 4.1 发送消息（HTTP 备用通道）

WebSocket 不可用时的降级方案。正常情况下消息通过 WebSocket 发送。

```
POST /api/v1/messages
```

**请求体：**

```json
{
    "sender_id": "my_device_uuid",
    "receiver_id": "target_device_uuid",
    "content": "你好",
    "type": "common"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sender_id | string | ✓ | 发送者 device_id |
| receiver_id | string | ✓ | 接收者 device_id |
| content | string | ✓ | 消息内容（最长 1000 字符） |
| type | string | ✓ | 消息类型，见下表 |

**消息类型枚举：**

| type 值 | 说明 |
|---------|------|
| `common` | 普通文本消息 |
| `heartbeat` | 心跳消息（附近存在感通知） |

**响应：**

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

**Server 行为：**
1. 检查发送者是否被接收者屏蔽 → 4004
2. 判断好友关系：
   - 好友：直接发送，无限制
   - 非好友：检查临时会话，未回复前最多 2 条 → 4001
3. 若非好友且无临时会话，自动创建临时会话（`is_temp = true`）
4. 存入 messages 表
5. 通过 WebSocket 实时推送给接收者（**不判断接收者是否在线，始终推送**）

---

### 4.2 获取历史消息

```
GET /api/v1/messages/{session_id}
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 请求者 device_id（权限校验） |
| before | string | ✗ | 分页游标，返回此时间之前的消息（ISO 8601） |
| after | string | ✗ | 增量游标，返回此时间之后的消息（ISO 8601） |
| limit | int | ✗ | 每页条数，默认 20，最大 50 |

**响应：**

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

**说明：**
- `before` 用于向后翻页（更早的消息）
- `after` 用于向前补漏（更新的消息）
- 若同时传入 `before` 和 `after`，优先按 `after` 处理

---

### 4.3 全局消息同步

```
GET /api/v1/messages/sync
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 当前设备 ID |
| after | string | ✓ | 返回此时间之后收到的消息（ISO 8601） |
| limit | int | ✗ | 每次最多返回条数，默认 200，最大 500 |

**响应：**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "messages": [
            {
                "message_id": "msg-uuid",
                "session_id": "session-uuid",
                "sender_id": "peer-device-uuid",
                "receiver_id": "my-device-uuid",
                "content": "你好",
                "type": "common",
                "created_at": "2026-03-14T10:53:00Z"
            }
        ],
        "has_more": false
    }
}
```

**Local App 行为：** WebSocket 重连成功或 App 需要全局补漏时，按本地最新接收时间调用该接口。

**Server 行为：** 返回 `receiver_id = device_id` 且 `created_at > after` 的消息；`heartbeat` 不进入补漏列表。

---

### 4.4 标记消息已读

```
POST /api/v1/messages/read
```

**请求体：**

```json
{
    "device_id": "my_device_uuid",
    "message_ids": ["msg-uuid-1", "msg-uuid-2"]
}
```

**响应：**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "updated_count": 2
    }
}
```

**Server 行为：** 更新 messages 表中对应记录的 `status = read`、`read_at = now()`，并通过 WebSocket 通知发送者已读。

---

## 5. Relation Service（好友关系服务）

### 5.1 获取好友列表

```
GET /api/v1/friends
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 自身 device_id |

**响应：**

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

---

### 5.1.1 获取待处理好友申请

```
GET /api/v1/friends/requests
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 接收方 device_id |

**响应：**

```json
{
    "code": 0,
    "message": "ok",
    "data": {
        "requests": [
            {
                "request_id": "friendship-uuid",
                "sender_id": "sender-device-uuid",
                "nickname": "小明",
                "avatar": "https://cdn.example.com/avatar.jpg",
                "tags": ["摄影"],
                "message": "想加你为好友",
                "created_at": "2026-03-15T09:00:00Z"
            }
        ]
    }
}
```

**说明：**
- 返回当前设备收到的 `pending` 状态好友申请
- 客户端可在好友页进入时或轮询时调用，作为 `friend_request` WebSocket 的兜底同步

---

### 5.2 发送好友申请

```
POST /api/v1/friends/request
```

**请求体：**

```json
{
    "sender_id": "my_device_uuid",
    "receiver_id": "target_device_uuid",
    "message": "想加你为好友"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sender_id | string | ✓ | 申请者 device_id |
| receiver_id | string | ✓ | 目标 device_id |
| message | string | ✗ | 验证消息（最长 200 字符） |

**响应：**

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

**Server 行为：**
1. 检查是否被屏蔽 → 4004
2. 检查 24h 冷却 → 4005
3. 检查是否重复申请 → 4009
4. 创建 friendships 记录（`status = pending`）
5. 通过 WebSocket 推送 `friend_request` 给接收方

> **注意**: Server 不检查对方是否在 chatable 范围内，此校验由客户端在发送前完成。

---

### 5.3 回应好友申请

```
PUT /api/v1/friends/{request_id}
```

**请求体：**

```json
{
    "device_id": "my_device_uuid",
    "action": "accept"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 操作者 device_id |
| action | string | ✓ | `accept` 或 `reject` |

**响应（accept）：**

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

| 字段 | 说明 |
|------|------|
| session_id | 好友长期会话 ID（`is_temp = false`），双方后续使用此会话聊天 |

**响应（reject）：**

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

**Server 行为：**
1. accept：更新 friendships 为 `accepted`，创建永久会话，若之前有临时会话则升级为永久
2. reject：更新 friendships 为 `rejected`，记录拒绝时间（用于 24h 冷却）
3. 通过 WebSocket 通知申请方结果

**好友关系状态枚举**: `pending`, `accepted`, `rejected`

---

### 5.4 删除好友

```
DELETE /api/v1/friends/{friend_device_id}
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 操作者 device_id |

**响应：**

```json
{
    "code": 0,
    "message": "ok",
    "data": null
}
```

**Server 行为：** 删除 friendships 记录，并立刻将该对设备的现有永久会话标记为过期；若对方在线，额外通过 WebSocket 推送 `friend_deleted`，要求客户端移除本地好友关系并停止继续远距发送。

---

### 5.5 屏蔽用户

```
POST /api/v1/block
```

**请求体：**

```json
{
    "device_id": "my_device_uuid",
    "target_id": "target_device_uuid"
}
```

**响应：**

```json
{
    "code": 0,
    "message": "ok",
    "data": null
}
```

**Server 行为：** 屏蔽后双方互不可见——附近列表不显示、消息不可达、好友申请不可发。若存在好友关系，删除好友关系。

---

### 5.6 取消屏蔽

```
DELETE /api/v1/block/{target_device_id}
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | ✓ | 操作者 device_id |

**响应：**

```json
{
    "code": 0,
    "message": "ok",
    "data": null
}
```

---

## 6. WebSocket 协议

### 6.1 连接

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

> **注意**: Server 不维护设备在线状态，WebSocket 连接仅用于实时消息推送。

---

### 6.2 客户端 → 服务器

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

> 消息类型与 HTTP 接口一致：`common` / `heartbeat`

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

客户端每 30 秒发送一次（WebSocket 连接保活，与业务 heartbeat 消息不同）：

```json
{
    "action": "ping"
}
```

---

### 6.3 服务器 → 客户端

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

#### 消息发送确认

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

#### 好友关系被移除

```json
{
    "type": "friend_deleted",
    "payload": {
        "peer_device_id": "other-device-uuid"
    }
}
```

说明：当对方删除好友或拉黑当前用户时，服务端推送该事件，客户端应立即移除本地好友关系，并把对应聊天降级为不可继续远距发送的状态。

#### Boost 提示（好友重新接近）

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

#### 心跳响应

```json
{
    "type": "pong"
}
```

#### 错误通知

```json
{
    "type": "error",
    "payload": {
        "code": 4001,
        "message": "临时聊天消息已达上限"
    }
}
```

---

## 7. Heartbeat 机制说明

Heartbeat 解决 BLE 扫描的单向性问题：A 扫到 B，但 B 未扫到 A。

**流程：**

1. A 通过 BLE 扫描发现 B
2. A 通过 WebSocket（或 HTTP）向 B 发送 `type: heartbeat` 消息
3. B 收到后将 A 加入本地 `heartbeat_receive` 列表
4. B 的 `chatable` 列表 = `ble_find ∪ heartbeat_receive`

**频率：** 每 5 秒一次（向 `ble_find` 列表中的设备发送）。

**Local App 本地数据结构：**

| 列表 | 更新方式 | 说明 |
|------|----------|------|
| `ble_find` | BLE 扫描结果（每 5-10 秒刷新） | 本机直接扫描发现的设备 |
| `heartbeat_receive` | 收到 heartbeat 消息时更新 | 对方扫到我并通知我 |
| `chatable` | 实时计算 `ble_find ∪ heartbeat_receive` | 最终的"附近可聊天"列表 |
| `friend` | 好友申请被接受后更新 | 好友列表 |
| `block` | 本地屏蔽操作后更新 | 屏蔽列表（本地过滤用） |

> heartbeat 消息由服务器透传，不做业务处理。服务器仅负责转发。

---

## 8. 会话（Session）模型

| 字段 | 说明 |
|------|------|
| session_id | UUID，服务器生成 |
| device_a_id | 参与方 A（`device_a_id < device_b_id`） |
| device_b_id | 参与方 B |
| is_temp | `true` = 临时会话（非好友）；`false` = 好友长期会话 |
| last_message_at | 最后一条消息的时间 |
| expires_at | 临时会话过期时间（客户端上报离开后设置） |
| status | `active` / `expired` |

**临时会话规则：**
- 非好友首次发消息时自动创建（`is_temp = true`）
- 未回复前发送方最多 2 条消息
- 客户端检测到蓝牙断开 1 分钟后上报，服务器标记会话过期，推送 `session_expired`
- 好友申请通过后，临时会话升级为永久会话（`is_temp = false`）

---

## 9. 接口清单速查

### REST API

| 方法 | 路径 | 服务 | 说明 |
|------|------|------|------|
| POST | `/api/v1/device/init` | Device | 设备初始化 |
| GET | `/api/v1/device/{device_id}` | Device | 获取设备资料 |
| PUT | `/api/v1/device/{device_id}` | Device | 更新设备资料 |
| POST | `/api/v1/temp-id/refresh` | TempID | 刷新临时 BLE 广播 ID |
| POST | `/api/v1/presence/resolve` | Presence | 解析附近设备 |
| POST | `/api/v1/presence/disconnect` | Presence | 上报设备离开范围 |
| POST | `/api/v1/messages` | Messaging | 发送消息（HTTP 备用） |
| GET | `/api/v1/messages/{session_id}` | Messaging | 获取历史消息 / 单会话增量同步 |
| GET | `/api/v1/messages/sync` | Messaging | 全局消息补漏 |
| POST | `/api/v1/messages/read` | Messaging | 标记已读 |
| GET | `/api/v1/friends` | Relation | 获取好友列表 |
| GET | `/api/v1/friends/requests` | Relation | 获取待处理好友申请 |
| POST | `/api/v1/friends/request` | Relation | 发送好友申请 |
| PUT | `/api/v1/friends/{request_id}` | Relation | 回应好友申请（action: accept/reject） |
| DELETE | `/api/v1/friends/{friend_device_id}` | Relation | 删除好友 |
| POST | `/api/v1/block` | Relation | 屏蔽用户 |
| DELETE | `/api/v1/block/{target_device_id}` | Relation | 取消屏蔽 |

### WebSocket

| 方向 | type / action | 说明 |
|------|---------------|------|
| C → S | `send_message` | 发送消息 |
| C → S | `mark_read` | 标记已读 |
| C → S | `ping` | 心跳保活（WebSocket 连接层） |
| S → C | `connected` | 连接确认 |
| S → C | `message_sent` | 消息发送确认 |
| S → C | `new_message` | 新消息推送 |
| S → C | `friend_request` | 好友申请推送 |
| S → C | `friend_response` | 好友申请结果 |
| S → C | `friend_deleted` | 对方移除好友关系 |
| S → C | `boost` | 好友重新接近提示 |
| S → C | `session_expired` | 临时会话过期 |
| S → C | `messages_read` | 已读回执 |
| S → C | `pong` | 心跳响应 |
| S → C | `error` | 错误通知 |

---

## 10. 变更日志

### V3 (2026-03-14)

- **修改** 心跳频率：由"约1Hz（每秒1次）"改为"每 5 秒一次"
- **明确** Server 不管理设备在线状态，离线判断完全由客户端负责
- **删除** `presence` 表的 `is_online` 字段概念
- **修正** 错误码 5002 含义：由"设备不在线"改为"服务器内部错误"
- **补充** WebSocket `message_sent` 响应类型
- **补充** WebSocket `error` 响应类型
- **补充** `GET /api/v1/messages/sync` 作为全局消息补漏接口
- **扩展** `GET /api/v1/messages/{session_id}` 支持 `after` 增量同步
- **收口** block 路径为 `/api/v1/block`
- **统一** 字段命名：`scanned_devices`（非 `temp_ids`）、`boost_alerts`（非 `boost_triggered`）、`distance_estimate`（非 `distance`）
- **统一** 消息类型：使用 `common`（非 `text`）
- **统一** 好友申请响应：使用 `action` 字段（非独立端点）
- **统一** 好友关系状态：`pending`, `accepted`, `rejected`（`blocked` 在独立表）
