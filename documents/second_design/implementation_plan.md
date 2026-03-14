# NotePassing 实现计划 (Implementation Plan)

> 基于 [Unified API Contract V2](./unified_api_contract_v2.md) 拆分实现步骤
> **创建日期**: 2026-03-14

---

## 阶段划分概览

| 阶段 | 名称 | 目标 | 预估工时 |
|------|------|------|---------|
| Phase 0 | 基础设施 | 项目搭建、数据库、工具链 | 1-2 天 |
| Phase 1 | Device 模块 | 设备注册、资料管理 | 1 天 |
| Phase 2 | Temp ID 模块 | 临时 ID 生成与刷新 | 0.5 天 |
| Phase 3 | Presence 模块 | 附近关系、BLE 解析 | 1 天 |
| Phase 4 | Messaging 模块 | 消息存储、HTTP 接口 | 1 天 |
| Phase 5 | Relation 模块 | 好友关系、屏蔽功能 | 1 天 |
| Phase 6 | WebSocket 模块 | 实时通信、事件推送 | 1.5 天 |
| Phase 7 | 联调测试 | 集成测试、Bug 修复 | 2 天 |

---

## Phase 0: 基础设施 (Foundation)

### 0.1 后端项目初始化
**任务**: 创建 FastAPI 项目基础结构

- [ ] 创建项目目录结构
  ```
  backend/
  ├── app/
  │   ├── __init__.py
  │   ├── main.py              # FastAPI 入口
  │   ├── config.py            # 配置管理
  │   ├── dependencies.py      # 依赖注入
  │   ├── database.py          # 数据库连接
  │   ├── models/              # SQLAlchemy ORM 模型
  │   ├── schemas/             # Pydantic 数据模型
  │   ├── routers/             # API 路由
  │   ├── services/            # 业务逻辑层
  │   └── utils/               # 工具函数
  ├── tests/
  ├── alembic/                 # 数据库迁移
  ├── requirements.txt
  └── Dockerfile
  ```
- [ ] 配置环境变量管理 (.env / pydantic-settings)
- [ ] 配置日志系统 (structlog / standard logging)
- [ ] 添加健康检查端点 `GET /health`

**验收标准**: 项目可启动，Swagger UI 可访问

### 0.2 数据库设计与初始化
**任务**: 设计并创建数据库表结构

- [ ] 配置 SQLAlchemy + asyncpg (异步 PostgreSQL)
- [ ] 创建数据库模型 (见 0.2.1)
- [ ] 配置 Alembic 迁移工具
- [ ] 创建初始迁移脚本
- [ ] 编写数据库连接池管理

#### 0.2.1 数据模型定义

| 模型名 | 文件名 | 核心字段 |
|--------|--------|---------|
| Device | `device.py` | `device_id(PK)`, `nickname`, `avatar`, `tags`, `profile`, `is_anonymous`, `role_name`, `created_at`, `updated_at` |
| TempID | `temp_id.py` | `temp_id(PK)`, `device_id(FK)`, `created_at`, `expires_at` |
| Presence | `presence.py` | `id(PK)`, `device_id`, `nearby_device_id`, `rssi`, `last_seen_at` |
| Session | `session.py` | `session_id(PK)`, `device_a_id`, `device_b_id`, `is_temp`, `status`, `last_message_at`, `expires_at` |
| Message | `message.py` | `message_id(PK)`, `session_id(FK)`, `sender_id`, `receiver_id`, `content`, `type`, `status`, `created_at`, `read_at` |
| Friendship | `friendship.py` | `request_id(PK)`, `sender_id`, `receiver_id`, `status`, `message`, `created_at`, `updated_at`, `rejected_at` |
| Block | `block.py` | `id(PK)`, `device_id`, `target_id`, `created_at` |
| WebSocketConnection | `ws_connection.py` | `id(PK)`, `device_id`, `connection_id`, `connected_at` |

**验收标准**: 所有表可通过迁移创建，模型单元测试通过

### 0.3 通用模块实现
**任务**: 构建共享基础设施

- [ ] **响应包装器** (`utils/response.py`)
  - `success_response(data, message="ok")` → `{"code": 0, "message": "ok", "data": ...}`
  - `error_response(code, message)` → 标准错误格式
  
- [ ] **异常处理** (`utils/exceptions.py`)
  - 自定义异常基类 `NotePassingException`
  - 业务异常: `DeviceNotFoundError`, `TempIDExpiredError`, `BlockedError`, etc.
  - 全局异常处理器 (FastAPI exception handler)

- [ ] **错误码常量** (`utils/error_codes.py`)
  ```python
  SUCCESS = 0
  TEMP_CHAT_LIMIT_REACHED = 4001
  TEMP_SESSION_EXPIRED = 4002
  NOT_IN_BLUETOOTH_RANGE = 4003
  BLOCKED_BY_USER = 4004
  FRIEND_REQUEST_COOLDOWN = 4005
  INVALID_TEMP_ID = 4006
  DEVICE_NOT_INITIALIZED = 4007
  FRIENDSHIP_NOT_EXIST = 4008
  DUPLICATE_OPERATION = 4009
  INVALID_PARAMS = 5001
  SERVER_ERROR = 5002
  ```

- [ ] **UUID 工具** (`utils/uuid.py`)
  - `generate_device_id()` → UUID v4
  - `generate_temp_id(device_id: str) -> str` → 32位十六进制字符串
  - 生成规则: `hex(hash(device_id + secret_key + timestamp + random_salt))`

- [ ] **验证工具** (`utils/validators.py`)
  - `validate_device_id(device_id: str) -> bool`
  - `validate_temp_id(temp_id: str) -> bool`

**验收标准**: 所有工具函数有单元测试覆盖

---

## Phase 1: Device Service 模块

### 1.1 设备初始化 API
**Endpoint**: `POST /api/v1/device/init`

- [ ] 创建 Pydantic Schema
  - `DeviceInitRequest`: device_id, nickname, tags[], profile
  - `DeviceInitResponse`: device_id, nickname, is_new, created_at

- [ ] 实现 Service 层
  - `DeviceService.init_device()` - 创建或恢复设备
  - 检查 device_id 是否存在 → 返回 is_new: false
  - 不存在 → 创建新记录 → 返回 is_new: true

- [ ] 实现 Router
  - 参数校验
  - 调用 Service
  - 返回统一响应格式

**验收标准**: 
- 新设备首次注册返回 `is_new: true` (HTTP 201)
- 已有设备恢复返回 `is_new: false` (HTTP 200)
- 字段格式错误返回 `code: 5001`

### 1.2 获取设备资料 API
**Endpoint**: `GET /api/v1/device/{device_id}?requester_id={requester_id}`

- [ ] 创建 Pydantic Schema
  - `DeviceProfileResponse`: 按隐私规则过滤后的字段

- [ ] 实现 Service 层
  - `DeviceService.get_device_profile(target_id, requester_id)`
  - 检查是否为好友 → 决定可见字段
  - 匿名模式处理: 陌生人隐藏 avatar，显示 role_name

- [ ] 实现 Router
  - 路径参数: device_id
  - 查询参数: requester_id

**验收标准**:
- 好友请求返回完整信息 (含 device_id, avatar)
- 陌生人匿名请求隐藏 avatar，返回 role_name
- 陌生人非匿名请求显示 avatar，不返回 role_name

### 1.3 更新设备资料 API
**Endpoint**: `PUT /api/v1/device/{device_id}`

- [ ] 创建 Pydantic Schema
  - `DeviceUpdateRequest`: nickname, avatar, tags[], profile, is_anonymous, role_name (全部可选)
  - `DeviceUpdateResponse`: 更新后的完整资料

- [ ] 实现 Service 层
  - `DeviceService.update_device()` - 部分更新
  - 只更新传入的字段
  - 更新 `updated_at` 字段

- [ ] 实现 Router

**验收标准**: 部分更新成功，未传字段保持不变

---

## Phase 2: Temp ID Service 模块

### 2.1 临时 ID 刷新 API
**Endpoint**: `POST /api/v1/temp-id/refresh`

- [ ] 创建 Pydantic Schema
  - `TempIDRefreshRequest`: device_id, current_temp_id(可选)
  - `TempIDRefreshResponse`: temp_id, expires_at

- [ ] 实现 Service 层
  - `TempIDService.refresh_temp_id(device_id, current_temp_id)`
  - 生成新 temp_id (32字符十六进制)
  - 设置过期时间 (建议5分钟 + 5分钟缓冲 = 10分钟)
  - 如有 current_temp_id，缩短其过期时间至5分钟后

- [ ] 实现 Router

**验收标准**:
- 返回的 temp_id 格式正确 (32字符十六进制)
- expires_at 是有效的 ISO 8601 时间
- 传入旧 temp_id 后，旧 ID 在5分钟后过期

---

## Phase 3: Presence Service 模块

### 3.1 解析附近设备 API
**Endpoint**: `POST /api/v1/presence/resolve`

- [ ] 创建 Pydantic Schema
  - `ScannedDevice`: temp_id, rssi
  - `PresenceResolveRequest`: device_id, scanned_devices[]
  - `NearbyDevice`: temp_id, device_id, nickname, avatar, tags, profile, is_anonymous, role_name, distance_estimate, is_friend
  - `BoostAlert`: device_id, nickname, distance_estimate
  - `PresenceResolveResponse`: nearby_devices[], boost_alerts[]

- [ ] 实现 Service 层
  - `PresenceService.resolve_nearby_devices(device_id, scanned_devices)`
  - 查询 temp_ids 表解析 device_id
  - 过滤被屏蔽的设备 (Block 表)
  - 计算 distance_estimate (基于 RSSI 的简单算法)
  - 根据好友关系和隐私规则过滤返回字段
  - 更新 presence 表 (last_seen_at)
  - 检测 Boost 条件 (好友从离开变为附近且 ≥5分钟)

- [ ] 实现 RSSI 到距离估算算法
  ```python
  # 简化算法，可基于实际测试调整
  def estimate_distance(rssi: int) -> float:
      # 参考值: RSSI -65 约等于 2.5 米
      tx_power = -59  # 1米处的参考RSSI
      ratio = rssi / tx_power
      if ratio < 1.0:
          return pow(ratio, 10)
      else:
          return 0.89976 * pow(ratio, 7.7095) + 0.111
  ```

- [ ] 实现 Router

**验收标准**:
- 正确解析 temp_id 到 device_id
- 返回的距离估算合理
- 被屏蔽设备不出现在结果中
- 好友 Boost 条件正确触发

### 3.2 上报离开范围 API
**Endpoint**: `POST /api/v1/presence/disconnect`

- [ ] 创建 Pydantic Schema
  - `PresenceDisconnectRequest`: device_id, left_device_id
  - `PresenceDisconnectResponse`: session_expired, session_id(可选)

- [ ] 实现 Service 层
  - `PresenceService.report_disconnect(device_id, left_device_id)`
  - 更新 presence 表 (last_seen_at)
  - 检查是否存在临时会话 → 标记为过期
  - 返回是否有过期会话

- [ ] 实现 Router

**验收标准**: 临时会话正确标记过期，返回 session_expired 标志

---

## Phase 4: Messaging Service 模块

### 4.1 发送消息 API (HTTP 备用)
**Endpoint**: `POST /api/v1/messages`

- [ ] 创建 Pydantic Schema
  - `SendMessageRequest`: sender_id, receiver_id, content, type
  - `SendMessageResponse`: message_id, session_id, status, created_at

- [ ] 实现 Service 层
  - `MessageService.send_message()`
  - 检查屏蔽 → 4004
  - 检查好友关系
    - 好友: 获取/创建永久会话
    - 非好友: 检查临时会话，未回复前最多2条 → 4001
  - 非好友无会话时自动创建临时会话
  - 存入 messages 表
  - WebSocket 推送 (若接收者在线)

- [ ] 实现 Router

**验收标准**:
- 被屏蔽发送返回 4004
- 非好友未回复超过2条返回 4001
- 消息正确创建，返回 message_id

### 4.2 获取历史消息 API
**Endpoint**: `GET /api/v1/messages/{session_id}?device_id={device_id}&before={before}&limit={limit}`

- [ ] 创建 Pydantic Schema
  - `MessageHistoryItem`: message_id, sender_id, content, type, status, created_at
  - `MessageHistoryResponse`: session_id, messages[], has_more

- [ ] 实现 Service 层
  - `MessageService.get_history(session_id, device_id, before, limit)`
  - 权限校验 (device_id 必须是会话参与者)
  - 分页查询 (默认20条，最大50条)

- [ ] 实现 Router

**验收标准**: 分页正确，非参与者无法获取消息

### 4.3 标记已读 API
**Endpoint**: `POST /api/v1/messages/read`

- [ ] 创建 Pydantic Schema
  - `MarkReadRequest`: device_id, message_ids[]
  - `MarkReadResponse`: updated_count

- [ ] 实现 Service 层
  - `MessageService.mark_read(device_id, message_ids)`
  - 更新 messages 表 (status=read, read_at=now())
  - WebSocket 通知发送者

- [ ] 实现 Router

**验收标准**: 正确更新已读状态，WebSocket 推送已读回执

---

## Phase 5: Relation Service 模块

### 5.1 获取好友列表 API
**Endpoint**: `GET /api/v1/friends?device_id={device_id}`

- [ ] 创建 Pydantic Schema
  - `FriendItem`: device_id, nickname, avatar, tags, profile, is_anonymous, last_chat_at
  - `FriendListResponse`: friends[]

- [ ] 实现 Service 层
  - `RelationService.get_friends(device_id)`
  - 查询 friendships 表 (status=accepted)
  - 联表查询设备资料

- [ ] 实现 Router

### 5.2 发送好友申请 API
**Endpoint**: `POST /api/v1/friends/request`

- [ ] 创建 Pydantic Schema
  - `FriendRequestRequest`: sender_id, receiver_id, message(可选)
  - `FriendRequestResponse`: request_id, status, created_at

- [ ] 实现 Service 层
  - `RelationService.send_friend_request()`
  - 检查屏蔽 → 4004
  - 检查24h冷却 (rejected_at) → 4005
  - 检查重复申请 → 4009
  - 创建 friendships 记录 (status=pending)
  - WebSocket 推送通知

- [ ] 实现 Router

**验收标准**:
- 被屏蔽返回 4004
- 冷却期内返回 4005
- 重复申请返回 4009

### 5.3 回应好友申请 API
**Endpoint**: `PUT /api/v1/friends/{request_id}`

- [ ] 创建 Pydantic Schema
  - `FriendResponseRequest`: device_id, action (accept/reject)
  - `FriendResponseResponse`: request_id, status, friend(可选), session_id(可选)

- [ ] 实现 Service 层
  - `RelationService.respond_friend_request(request_id, device_id, action)`
  - accept: 更新为 accepted，创建永久会话，升级临时会话
  - reject: 更新为 rejected，记录 rejected_at
  - WebSocket 通知申请方

- [ ] 实现 Router

### 5.4 删除好友 API
**Endpoint**: `DELETE /api/v1/friends/{friend_device_id}?device_id={device_id}`

- [ ] 实现 Service 层
  - `RelationService.delete_friend(device_id, friend_device_id)`
  - 删除 friendships 记录
  - 可选: 会话降级为临时会话

- [ ] 实现 Router

### 5.5 屏蔽用户 API
**Endpoint**: `POST /api/v1/block`

- [ ] 创建 Pydantic Schema
  - `BlockRequest`: device_id, target_id

- [ ] 实现 Service 层
  - `RelationService.block_user()`
  - 创建 block 记录
  - 如有好友关系，删除好友关系

- [ ] 实现 Router

### 5.6 取消屏蔽 API
**Endpoint**: `DELETE /api/v1/block/{target_device_id}?device_id={device_id}`

- [ ] 实现 Service 层
  - `RelationService.unblock_user()`
  - 删除 block 记录

- [ ] 实现 Router

---

## Phase 6: WebSocket 模块

### 6.1 WebSocket 连接管理

- [ ] 实现连接管理器 (`services/websocket_manager.py`)
  - `ConnectionManager` 类
  - `connect(device_id, websocket)`: 建立连接，存储 mapping
  - `disconnect(device_id)`: 断开连接，清理 mapping
  - `send_personal_message(device_id, message)`: 向指定设备发送
  - `is_connected(device_id) -> bool`: 检查是否在线

- [ ] 实现 WebSocket 端点 (`routers/websocket.py`)
  - `WSS /api/v1/ws?device_id={device_id}`
  - 连接建立时推送 `connected` 事件
  - 消息循环处理客户端消息

### 6.2 客户端 → 服务器消息处理

- [ ] 实现消息解析器
  - `action: send_message` → 调用 MessageService
  - `action: mark_read` → 调用 MessageService.mark_read
  - `action: ping` → 返回 `pong`

- [ ] 实现消息 Schema
  - `WebSocketSendMessage`: receiver_id, content, type
  - `WebSocketMarkRead`: message_ids[]

### 6.3 服务器 → 客户端消息推送

- [ ] 实现各事件类型的推送函数
  - `push_new_message(receiver_id, message_data)`
  - `push_message_sent(sender_id, message_data)`
  - `push_friend_request(receiver_id, request_data)`
  - `push_friend_response(receiver_id, response_data)`
  - `push_boost(receiver_id, boost_data)`
  - `push_session_expired(receiver_ids[], session_data)`
  - `push_messages_read(sender_id, read_data)`
  - `push_error(device_id, error_data)`

### 6.4 与 HTTP Service 集成

- [ ] 修改各 Service 方法，在业务操作后调用 WebSocket 推送
  - `MessageService.send_message()` → 推送 new_message / message_sent
  - `MessageService.mark_read()` → 推送 messages_read
  - `RelationService.send_friend_request()` → 推送 friend_request
  - `RelationService.respond_friend_request()` → 推送 friend_response
  - `PresenceService.report_disconnect()` → 推送 session_expired
  - `PresenceService.resolve_nearby_devices()` → 推送 boost

**验收标准**: 所有实时事件正确推送，断线重连后消息不丢失

---

## Phase 7: 联调测试

### 7.1 单元测试

- [ ] 各 Service 方法单元测试
- [ ] 各 Router 端点测试 (使用 TestClient)
- [ ] WebSocket 连接测试

### 7.2 集成测试

- [ ] 完整业务流程测试
  - 设备A、B初始化
  - A扫描到B的temp_id
  - 双方交换资料
  - 发送消息 (临时会话)
  - 添加好友
  - 好友消息
  - 离开范围

### 7.3 性能测试

- [ ] WebSocket 并发连接测试
- [ ] 消息吞吐量测试
- [ ] 数据库查询优化

### 7.4 部署准备

- [ ] Dockerfile 优化
- [ ] docker-compose.yml (含 PostgreSQL)
- [ ] 环境变量配置文档
- [ ] API 文档 (Swagger) 确认

---

## 文件清单 (后端)

### 模型文件 (app/models/)
```
device.py
temp_id.py
presence.py
session.py
message.py
friendship.py
block.py
ws_connection.py
```

### Schema 文件 (app/schemas/)
```
device.py
temp_id.py
presence.py
message.py
friendship.py
block.py
websocket.py
common.py          # 通用响应格式
```

### Service 文件 (app/services/)
```
device_service.py
temp_id_service.py
presence_service.py
message_service.py
relation_service.py
websocket_manager.py
```

### Router 文件 (app/routers/)
```
device.py
temp_id.py
presence.py
message.py
friendship.py
block.py
websocket.py
```

### 工具文件 (app/utils/)
```
response.py
exceptions.py
error_codes.py
uuid.py
validators.py
distance.py        # RSSI 转距离
```

---

## 注意事项

### 1. Server 不管理在线状态
- 数据库表不要有 `is_online` 字段
- 仅记录 `last_seen_at`
- WebSocket 连接仅用于消息推送，不代表"在线状态"

### 2. 心跳机制
- 业务 heartbeat: 每 5 秒通过消息发送
- WebSocket ping/pong: 每 30 秒 (连接层保活)

### 3. 隐私规则实现
- 获取资料时必须传入 requester_id
- Service 层负责根据关系过滤字段
- 陌生人看不到 device_id (只能看到 temp_id)

### 4. 临时会话规则
- 非好友首次发消息自动创建
- 未回复前最多 2 条消息
- 蓝牙断开 1 分钟后过期

### 5. 临时 ID 生成
- 使用 hash + salt 保证不可反推
- 过期时间: 5 分钟活跃期 + 5 分钟缓冲期

---

## 参考文档

- [Unified API Contract V2](./unified_api_contract_v2.md)
- FastAPI 文档: https://fastapi.tiangolo.com/
- SQLAlchemy 2.0 文档: https://docs.sqlalchemy.org/
