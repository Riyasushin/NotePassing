# NotePassing Server 测试列表 (Test List)

> 基于 Unified API Contract V2 的完整测试用例  
> **日期**: 2026-03-14

---

## 目录

1. [测试策略](#1-测试策略)
2. [单元测试](#2-单元测试)
3. [集成测试](#3-集成测试)
4. [端到端测试](#4-端到端测试)
5. [性能测试](#5-性能测试)

---

## 1. 测试策略

### 1.1 测试层级

```
┌─────────────────────────────────────────┐
│          E2E 测试 (端到端)               │  ← 完整用户流程
│         pytest + TestClient/WebSocket    │
├─────────────────────────────────────────┤
│          集成测试 (API)                  │  ← 多服务协作
│         pytest + FastAPI TestClient      │
├─────────────────────────────────────────┤
│          单元测试 (Service)              │  ← 单服务逻辑
│         pytest + mock                    │
└─────────────────────────────────────────┘
```

### 1.2 测试优先级

| 优先级 | 说明 | 覆盖率目标 |
|--------|------|-----------|
| P0 | 核心功能，阻塞性问题 | 100% |
| P1 | 重要功能 | 90%+ |
| P2 | 次要功能 | 70%+ |
| P3 | 边缘场景 | 50%+ |

---

## 2. 单元测试

### 2.1 DeviceService Tests

#### 2.1.1 `test_init_device_success_new_device` (P0)

**测试目标**: 新设备首次初始化成功

**前置条件**: 数据库为空

**测试步骤**:
1. 调用 `init_device(device_id="uuid-1", nickname="测试用户", tags=[], profile="")`

**期望结果**:
- 返回 `is_new: true`
- 数据库中创建 devices 记录
- 返回字段完整

---

#### 2.1.2 `test_init_device_success_existing_device` (P0)

**测试目标**: 已有设备恢复

**前置条件**: 数据库中存在 device_id="uuid-1"

**测试步骤**:
1. 调用 `init_device(device_id="uuid-1", nickname="新昵称", ...)`

**期望结果**:
- 返回 `is_new: false`
- 不修改原有记录

---

#### 2.1.3 `test_init_device_invalid_uuid` (P0)

**测试目标**: 无效 device_id 格式

**测试步骤**:
1. 调用 `init_device(device_id="invalid-id", ...)`

**期望结果**:
- 返回错误码 5001
- 错误信息包含 "device_id format error"

---

#### 2.1.4 `test_init_device_nickname_too_long` (P1)

**测试目标**: 昵称超长

**测试步骤**:
1. 调用 `init_device(nickname="a" * 51, ...)`

**期望结果**:
- 返回错误码 5001

---

#### 2.1.5 `test_get_device_profile_friend` (P0)

**测试目标**: 获取好友资料（完整信息）

**前置条件**: A 和 B 是好友

**测试步骤**:
1. A 调用 `get_device_profile(target_id=B, requester_id=A)`

**期望结果**:
- 返回完整资料包括 `avatar`
- `is_friend: true`

---

#### 2.1.6 `test_get_device_profile_stranger_anonymous` (P0)

**测试目标**: 获取陌生人匿名资料

**前置条件**: B 设置了 `is_anonymous: true`

**测试步骤**:
1. A 调用 `get_device_profile(target_id=B, requester_id=A)`

**期望结果**:
- 返回资料中 `avatar` 为 null 或隐藏
- `is_friend: false`
- 显示 `role_name`

---

#### 2.1.7 `test_update_device_partial` (P0)

**测试目标**: 部分更新设备资料

**前置条件**: 设备存在，原 nick="旧昵称", profile="旧简介"

**测试步骤**:
1. 调用 `update_device(device_id, {"nickname": "新昵称"})` （仅传 nickname）

**期望结果**:
- nickname 更新为 "新昵称"
- profile 保持 "旧简介"
- updated_at 更新

---

#### 2.1.8 `test_update_device_not_found` (P1)

**测试目标**: 更新不存在的设备

**测试步骤**:
1. 调用 `update_device(device_id="non-exist", {...})`

**期望结果**:
- 返回错误码 4007

---

### 2.2 TempIdService Tests

#### 2.2.1 `test_refresh_temp_id_success` (P0)

**测试目标**: 成功生成临时 ID

**测试步骤**:
1. 调用 `refresh_temp_id(device_id="uuid-1", current_temp_id=None)`

**期望结果**:
- 返回 32 字符十六进制 temp_id
- 返回 expires_at（5分钟后）
- 数据库 temp_ids 表存在记录

---

#### 2.2.2 `test_refresh_temp_id_with_current` (P0)

**测试目标**: 刷新时延长旧 ID 缓冲期

**前置条件**: 存在 current_temp_id="old-id"

**测试步骤**:
1. 调用 `refresh_temp_id(device_id="uuid-1", current_temp_id="old-id")`

**期望结果**:
- 生成新 temp_id
- 旧 ID 的 expires_at 更新为 "now + 5分钟"

---

#### 2.2.3 `test_refresh_temp_id_device_not_found` (P1)

**测试目标**: 为不存在设备生成 temp_id

**测试步骤**:
1. 调用 `refresh_temp_id(device_id="non-exist", ...)`

**期望结果**:
- 返回错误码 4007

---

#### 2.2.4 `test_resolve_temp_id_success` (P0)

**测试目标**: 成功解析有效 temp_id

**前置条件**: temp_id="abc123" 存在且未过期

**测试步骤**:
1. 调用 `resolve_temp_id("abc123")`

**期望结果**:
- 返回对应 device_id

---

#### 2.2.5 `test_resolve_temp_id_expired` (P0)

**测试目标**: 解析过期 temp_id

**前置条件**: temp_id="expired-id" 已过期

**测试步骤**:
1. 调用 `resolve_temp_id("expired-id")`

**期望结果**:
- 返回 None

---

#### 2.2.6 `test_resolve_temp_id_not_found` (P1)

**测试目标**: 解析不存在 temp_id

**测试步骤**:
1. 调用 `resolve_temp_id("non-exist")`

**期望结果**:
- 返回 None

---

### 2.3 PresenceService Tests

#### 2.3.1 `test_resolve_nearby_devices_success` (P0)

**测试目标**: 成功解析附近设备

**前置条件**:
- A 扫描到 temp_id_B, temp_id_C
- B 和 C 都是有效设备

**测试步骤**:
1. A 调用 `resolve_nearby_devices(device_id=A, scanned_devices=[B, C])`

**期望结果**:
- 返回 nearby_devices 列表包含 B 和 C 的资料
- 包含 distance_estimate

---

#### 2.3.2 `test_resolve_nearby_devices_filter_blocked` (P0)

**测试目标**: 过滤屏蔽设备

**前置条件**:
- A 扫描到 B 和 C
- A 屏蔽了 B

**测试步骤**:
1. A 调用 `resolve_nearby_devices(...)`

**期望结果**:
- nearby_devices 只包含 C
- 不包含 B

---

#### 2.3.3 `test_resolve_nearby_devices_boost_triggered` (P0)

**测试目标**: 触发 Boost 条件

**前置条件**:
- A 和 B 是好友
- A 最近 5 分钟未在附近发现 B

**测试步骤**:
1. A 调用 `resolve_nearby_devices(...包含B...)`

**期望结果**:
- boost_alerts 列表包含 B
- presence.last_boost_at 更新

---

#### 2.3.4 `test_resolve_nearby_devices_boost_cooldown` (P1)

**测试目标**: Boost 5分钟冷却

**前置条件**:
- A 和 B 是好友
- 2 分钟前刚触发过 Boost

**测试步骤**:
1. A 调用 `resolve_nearby_devices(...包含B...)`

**期望结果**:
- boost_alerts 为空

---

#### 2.3.5 `test_resolve_nearby_devices_anonymous_privacy` (P1)

**测试目标**: 匿名模式隐私过滤

**前置条件**:
- B 设置了 `is_anonymous: true`
- A 和 B 不是好友

**测试步骤**:
1. A 调用 `resolve_nearby_devices(...包含B...)`

**期望结果**:
- B 的资料中 avatar 为空
- 显示 role_name

---

#### 2.3.6 `test_report_disconnect_success` (P0)

**测试目标**: 上报离开范围成功

**前置条件**:
- A 和 B 存在 presence 记录
- 存在临时会话

**测试步骤**:
1. A 调用 `report_disconnect(device_id=A, left_device_id=B)`

**期望结果**:
- presence.last_disconnect_at 更新
- 临时会话标记为过期
- 返回 `session_expired: true`

---

#### 2.3.7 `test_report_disconnect_no_session` (P1)

**测试目标**: 离开范围无临时会话

**前置条件**: A 和 B 无临时会话

**测试步骤**:
1. A 调用 `report_disconnect(device_id=A, left_device_id=B)`

**期望结果**:
- 返回 `session_expired: false`

---

### 2.4 MessagingService Tests

#### 2.4.1 `test_send_message_friend_success` (P0)

**测试目标**: 好友间发送消息成功

**前置条件**: A 和 B 是好友

**测试步骤**:
1. A 调用 `send_message(sender_id=A, receiver_id=B, content="你好", type="common")`

**期望结果**:
- 消息存入数据库
- 返回 message_id, session_id
- 状态为 "sent"

---

#### 2.4.2 `test_send_message_blocked` (P0)

**测试目标**: 被屏蔽用户发送消息

**前置条件**: B 屏蔽了 A

**测试步骤**:
1. A 调用 `send_message(sender_id=A, receiver_id=B, ...)`

**期望结果**:
- 返回错误码 4004

---

#### 2.4.3 `test_send_message_stranger_first_two` (P0)

**测试目标**: 陌生人前两条消息成功

**前置条件**: A 和 B 不是好友，无历史消息

**测试步骤**:
1. A 发送第 1 条消息 → 成功
2. A 发送第 2 条消息 → 成功

**期望结果**:
- 两条消息都成功
- 自动创建临时会话

---

#### 2.4.4 `test_send_message_stranger_third_blocked` (P0)

**测试目标**: 陌生人第三条消息被限制

**前置条件**: A 已向 B 发送 2 条消息，B 未回复

**测试步骤**:
1. A 发送第 3 条消息

**期望结果**:
- 返回错误码 4001
- 消息未存入数据库

---

#### 2.4.5 `test_send_message_stranger_after_reply` (P0)

**测试目标**: 对方回复后可继续发送

**前置条件**: A 已向 B 发送 2 条消息

**测试步骤**:
1. B 回复 A 1 条消息
2. A 再次发送消息

**期望结果**:
- A 的消息成功发送

---

#### 2.4.6 `test_send_message_heartbeat` (P1)

**测试目标**: 发送心跳消息

**测试步骤**:
1. A 发送 `type="heartbeat"` 消息给 B

**期望结果**:
- 消息成功发送
- 透传至 B，服务器不做特殊处理

---

#### 2.4.7 `test_get_message_history_success` (P0)

**测试目标**: 获取历史消息

**前置条件**: 会话存在多条消息

**测试步骤**:
1. 调用 `get_message_history(session_id, device_id=A, before=None, limit=20)`

**期望结果**:
- 返回消息列表（倒序）
- 包含 has_more 标记

---

#### 2.4.8 `test_get_message_history_unauthorized` (P1)

**测试目标**: 无权限获取消息历史

**前置条件**: C 不是会话参与者

**测试步骤**:
1. C 调用 `get_message_history(session_id, device_id=C, ...)`

**期望结果**:
- 返回错误码 4008

---

#### 2.4.9 `test_mark_messages_read_success` (P0)

**测试目标**: 标记消息已读

**前置条件**: B 收到 A 的 2 条未读消息

**测试步骤**:
1. B 调用 `mark_messages_read(device_id=B, message_ids=[msg1, msg2])`

**期望结果**:
- 返回 updated_count: 2
- 消息状态更新为 "read"

---

#### 2.4.10 `test_mark_messages_read_only_receiver` (P1)

**测试目标**: 只有接收者能标记已读

**前置条件**: A 发送消息给 B

**测试步骤**:
1. A（发送者）调用 `mark_messages_read(device_id=A, message_ids=[msg1])`

**期望结果**:
- 返回 updated_count: 0

---

### 2.5 RelationService Tests

#### 2.5.1 `test_get_friends_list_success` (P0)

**测试目标**: 获取好友列表

**前置条件**: A 有 B、C 两个好友

**测试步骤**:
1. A 调用 `get_friends_list(device_id=A)`

**期望结果**:
- 返回好友列表包含 B 和 C
- 按最后聊天时间排序

---

#### 2.5.2 `test_send_friend_request_success` (P0)

**测试目标**: 发送好友申请成功

**前置条件**: A 和 B 不是好友，无待处理申请

**测试步骤**:
1. A 调用 `send_friend_request(sender_id=A, receiver_id=B, message="hi")`

**期望结果**:
- 创建 friendships 记录 status="pending"
- 返回 request_id

---

#### 2.5.3 `test_send_friend_request_blocked` (P0)

**测试目标**: 向屏蔽自己的用户发送申请

**前置条件**: B 屏蔽了 A

**测试步骤**:
1. A 调用 `send_friend_request(sender_id=A, receiver_id=B, ...)`

**期望结果**:
- 返回错误码 4004

---

#### 2.5.4 `test_send_friend_request_cooldown` (P0)

**测试目标**: 好友申请冷却期（24小时）

**前置条件**: 
- A 之前向 B 发送申请
- B 拒绝了申请（< 24小时）

**测试步骤**:
1. A 再次调用 `send_friend_request(sender_id=A, receiver_id=B, ...)`

**期望结果**:
- 返回错误码 4005

---

#### 2.5.5 `test_send_friend_request_duplicate` (P0)

**测试目标**: 重复发送好友申请

**前置条件**: A 已向 B 发送待处理申请

**测试步骤**:
1. A 再次调用 `send_friend_request(sender_id=A, receiver_id=B, ...)`

**期望结果**:
- 返回错误码 4009

---

#### 2.5.6 `test_respond_friend_request_accept` (P0)

**测试目标**: 接受好友申请

**前置条件**: B 收到 A 的好友申请（pending）

**测试步骤**:
1. B 调用 `respond_friend_request(request_id=xxx, device_id=B, action="accept")`

**期望结果**:
- friendships 状态更新为 "accepted"
- 创建永久会话
- 返回 session_id

---

#### 2.5.7 `test_respond_friend_request_accept_upgrade_session` (P0)

**测试目标**: 接受时升级临时会话

**前置条件**: 
- A 和 B 存在临时会话
- B 接受 A 的好友申请

**测试步骤**:
1. B 调用 `respond_friend_request(...action="accept")`

**期望结果**:
- 原临时会话 is_temp 更新为 false

---

#### 2.5.8 `test_respond_friend_request_reject` (P0)

**测试目标**: 拒绝好友申请

**前置条件**: B 收到 A 的好友申请

**测试步骤**:
1. B 调用 `respond_friend_request(request_id=xxx, device_id=B, action="reject")`

**期望结果**:
- friendships 状态更新为 "rejected"
- A 24小时内不能再申请

---

#### 2.5.9 `test_respond_friend_request_not_found` (P1)

**测试目标**: 回应不存在的申请

**测试步骤**:
1. 调用 `respond_friend_request(request_id="non-exist", ...)`

**期望结果**:
- 返回错误码 4008

---

#### 2.5.10 `test_delete_friend_success` (P0)

**测试目标**: 删除好友

**前置条件**: A 和 B 是好友

**测试步骤**:
1. A 调用 `delete_friend(device_id=A, friend_device_id=B)`

**期望结果**:
- friendships 记录删除
- 会话降级为临时会话（可选）

---

#### 2.5.11 `test_block_user_success` (P0)

**测试目标**: 屏蔽用户

**前置条件**: A 和 B 是好友

**测试步骤**:
1. A 调用 `block_user(device_id=A, target_id=B)`

**期望结果**:
- friendships 记录删除
- blocks 表添加记录
- presence 相关记录删除

---

#### 2.5.12 `test_block_user_not_friend` (P1)

**测试目标**: 屏蔽非好友

**前置条件**: A 和 B 不是好友

**测试步骤**:
1. A 调用 `block_user(device_id=A, target_id=B)`

**期望结果**:
- blocks 表添加记录
- 无异常

---

#### 2.5.13 `test_unblock_user_success` (P0)

**测试目标**: 取消屏蔽

**前置条件**: A 屏蔽了 B

**测试步骤**:
1. A 调用 `unblock_user(device_id=A, target_id=B)`

**期望结果**:
- blocks 记录删除

---

### 2.6 WebSocketManager Tests

#### 2.6.1 `test_connect_success` (P0)

**测试目标**: WebSocket 连接成功

**测试步骤**:
1. 客户端连接 `ws://.../ws?device_id=uuid-1`

**期望结果**:
- 连接成功
- 收到 `{"type": "connected", ...}` 消息
- connections 字典中存在该连接

---

#### 2.6.2 `test_disconnect_cleanup` (P0)

**测试目标**: 断开连接清理

**前置条件**: 设备已连接

**测试步骤**:
1. 客户端断开连接

**期望结果**:
- connections 字典中移除该连接

---

#### 2.6.3 `test_send_message_to_connected` (P0)

**测试目标**: 向已连接客户端发送消息

**前置条件**: B 已连接 WebSocket

**测试步骤**:
1. 调用 `send_message(device_id=B, message={...})`

**期望结果**:
- B 收到消息
- 返回 true

---

#### 2.6.4 `test_send_message_to_disconnected` (P1)

**测试目标**: 向未连接客户端发送消息

**前置条件**: B 未连接 WebSocket

**测试步骤**:
1. 调用 `send_message(device_id=B, message={...})`

**期望结果**:
- 返回 false
- 无异常抛出

---

#### 2.6.5 `test_handle_client_send_message` (P0)

**测试目标**: 处理客户端发送消息请求

**测试步骤**:
1. 客户端发送 `{"action": "send_message", "payload": {...}}`

**期望结果**:
- 调用 MessagingService.send_message
- 返回 message_sent 确认

---

#### 2.6.6 `test_handle_client_mark_read` (P0)

**测试目标**: 处理客户端标记已读请求

**测试步骤**:
1. 客户端发送 `{"action": "mark_read", "payload": {...}}`

**期望结果**:
- 调用 MessagingService.mark_messages_read
- 返回确认

---

#### 2.6.7 `test_handle_ping_pong` (P0)

**测试目标**: 心跳保活

**测试步骤**:
1. 客户端发送 `{"action": "ping"}`

**期望结果**:
- 收到 `{"type": "pong"}`

---

## 3. 集成测试

### 3.1 Device Flow Tests

#### 3.1.1 `test_device_full_lifecycle` (P0)

**测试目标**: 设备完整生命周期

**测试步骤**:
1. 初始化设备
2. 获取设备资料
3. 更新设备资料（部分更新）
4. 再次获取验证更新

**期望结果**: 全流程无异常

---

### 3.2 Presence Flow Tests

#### 3.2.1 `test_nearby_discovery_full_flow` (P0)

**测试目标**: 附近发现完整流程

**测试步骤**:
1. 设备 A 刷新 temp_id
2. 设备 B 刷新 temp_id
3. B 扫描到 A 的 temp_id，调用 resolve
4. A 扫描到 B 的 temp_id，调用 resolve
5. 验证双方都能获取对方资料

**期望结果**: 双方互相发现

---

#### 3.2.2 `test_boost_full_flow` (P0)

**测试目标**: Boost 触发完整流程

**测试步骤**:
1. A 和 B 成为好友
2. A 调用 resolve（不包含 B）
3. 等待 5 分钟冷却
4. A 调用 resolve（包含 B）
5. 验证 A 收到 boost 通知

**期望结果**: boost_alerts 包含 B

---

#### 3.2.3 `test_disconnect_expire_session` (P0)

**测试目标**: 离开范围会话过期

**测试步骤**:
1. A 和 B 非好友，建立临时会话（通过发消息）
2. A 调用 report_disconnect(B)
3. 验证会话已过期
4. 验证双方收到 session_expired WebSocket 消息

**期望结果**: 临时会话过期，WebSocket 通知送达

---

### 3.3 Messaging Flow Tests

#### 3.3.1 `test_message_http_and_websocket` (P0)

**测试目标**: HTTP 和 WebSocket 消息通道

**测试步骤**:
1. A 和 B 建立 WebSocket 连接
2. A 通过 WebSocket 发送消息给 B
3. 验证 B 收到 new_message
4. A 通过 HTTP POST 发送消息给 B
5. 验证 B 收到 new_message

**期望结果**: 双通道都正常工作

---

#### 3.3.2 `test_message_read_receipt_flow` (P0)

**测试目标**: 已读回执流程

**测试步骤**:
1. A 发送消息给 B
2. B 收到 WebSocket 消息
3. B 标记消息已读（WebSocket 或 HTTP）
4. A 收到 messages_read WebSocket 消息

**期望结果**: A 收到已读回执

---

### 3.4 Relation Flow Tests

#### 3.4.1 `test_friend_request_full_flow_accept` (P0)

**测试目标**: 好友申请接受完整流程

**测试步骤**:
1. A 发送好友申请给 B
2. B 收到 WebSocket friend_request
3. B 接受申请
4. A 收到 WebSocket friend_response
5. 验证双方好友列表包含对方
6. 验证永久会话创建

**期望结果**: 成为好友，有永久会话

---

#### 3.4.2 `test_friend_request_full_flow_reject` (P0)

**测试目标**: 好友申请拒绝完整流程

**测试步骤**:
1. A 发送好友申请给 B
2. B 拒绝申请
3. A 收到 WebSocket friend_response（rejected）
4. A 在 24 小时内再次申请

**期望结果**: 第二次申请返回 4005

---

#### 3.4.3 `test_block_blocks_all_interaction` (P0)

**测试目标**: 屏蔽阻断所有交互

**测试步骤**:
1. A 和 B 是好友
2. A 屏蔽 B
3. A 发送消息给 B → 应失败
4. B 发送消息给 A → 应失败
5. A 发送好友申请给 B → 应失败
6. B 出现在 A 的附近扫描 → 应被过滤

**期望结果**: 所有交互被阻断

---

### 3.5 Error Handling Tests

#### 3.5.1 `test_all_error_codes` (P1)

**测试目标**: 验证所有错误码

**测试步骤**: 触发各种错误场景

| 错误码 | 触发场景 | 验证 |
|--------|----------|------|
| 4001 | 陌生人发送第3条消息 | ✓ |
| 4002 | （如实现）临时会话过期后发消息 | ✓ |
| 4003 | （如实现）超出范围发消息 | ✓ |
| 4004 | 向屏蔽者发消息 | ✓ |
| 4005 | 被拒绝后24h内申请 | ✓ |
| 4006 | 使用过期 temp_id | ✓ |
| 4007 | 未初始化设备调用接口 | ✓ |
| 4008 | 操作不存在的好友关系 | ✓ |
| 4009 | 重复发送好友申请 | ✓ |
| 5001 | 无效参数格式 | ✓ |
| 5002 | （模拟）服务器内部错误 | ✓ |

---

## 4. 端到端测试

### 4.1 用户场景测试

#### 4.1.1 `test_scenario_first_meeting_become_friends` (P0)

**场景**: 两个陌生用户相遇并成为好友

**测试步骤**:
1. 用户 A 首次启动 App，初始化设备
2. 用户 B 首次启动 App，初始化设备
3. A 和 B 互相扫描到对方（BLE + temp_id 解析）
4. A 查看 B 的名片
5. A 向 B 发送临时消息（第1条）
6. B 收到消息并回复
7. A 和 B 开始聊天（超过2条消息限制）
8. A 发送好友申请
9. B 接受申请
10. A 和 B 成为好友，验证永久会话

**期望结果**: 完整流程成功

---

#### 4.1.2 `test_scenario_boost_reunion` (P0)

**场景**: 好友再次相遇触发 Boost

**测试步骤**:
1. A 和 B 是好友
2. A 和 B 都在线上但不在附近
3. A 进入 B 的蓝牙范围
4. A 的 App 扫描到 B，调用 resolve
5. 验证 A 收到 Boost 通知（震动 + UI 高亮）
6. 验证 B 也收到 Boost 通知

**期望结果**: 双方 Boost 触发

---

#### 4.1.3 `test_scenario_temp_chat_expire` (P0)

**场景**: 临时聊天因离开范围过期

**测试步骤**:
1. A 和 B 非好友，在附近
2. A 向 B 发送临时消息，建立临时会话
3. A 和 B 聊天（各发几条消息）
4. A 离开蓝牙范围超过 1 分钟
5. A 的 App 调用 disconnect
6. 验证 A 和 B 都收到 session_expired
7. 验证 A 无法再向 B 发送消息（或受限制）

**期望结果**: 临时会话正确过期

---

#### 4.1.4 `test_scenario_block_user` (P0)

**场景**: 用户屏蔽骚扰者

**测试步骤**:
1. A 和 B 是好友
2. B 频繁给 A 发消息
3. A 屏蔽 B
4. 验证 B 从 A 的好友列表消失
5. 验证 B 无法再发消息给 A
6. 验证 B 不会出现在 A 的附近列表
7. A 取消屏蔽 B
8. 验证 B 可以再次与 A 交互

**期望结果**: 屏蔽/取消屏蔽功能正常

---

#### 4.1.5 `test_scenario_anonymous_mode` (P1)

**场景**: 用户开启匿名模式

**测试步骤**:
1. A 设置 is_anonymous=true, role_name="神秘人"
2. B（非好友）扫描到 A
3. B 查看 A 的名片
4. 验证 B 看不到 A 的真实头像
5. 验证 B 看到 role_name "神秘人"
6. A 和 B 成为好友
7. B 再次查看 A 的名片
8. 验证 B 能看到 A 的真实头像和昵称

**期望结果**: 匿名模式隐私控制正常

---

### 4.2 并发测试

#### 4.2.1 `test_concurrent_nearby_resolve` (P1)

**测试目标**: 并发附近设备解析

**测试步骤**:
1. 100 个用户同时调用 resolve_nearby_devices
2. 每个用户扫描到 10 个其他用户

**期望结果**: 无死锁，响应时间 < 500ms

---

#### 4.2.2 `test_concurrent_message_send` (P1)

**测试目标**: 并发消息发送

**测试步骤**:
1. 两个用户同时给对方发送消息
2. 重复 100 次

**期望结果**: 消息无丢失，无重复

---

#### 4.2.3 `test_concurrent_friend_request` (P1)

**测试目标**: 并发好友申请

**测试步骤**:
1. A 向 B 发送好友申请
2. 同时 B 也向 A 发送好友申请

**期望结果**: 正确处理，不重复创建记录

---

## 5. 性能测试

### 5.1 API 性能基准

| 接口 | 目标响应时间 | 并发用户数 | 测试场景 |
|------|-------------|-----------|----------|
| POST /device/init | < 100ms | 100 | 新用户注册 |
| POST /temp-id/refresh | < 50ms | 500 | 定期刷新 |
| POST /presence/resolve | < 200ms | 200 | 附近发现 |
| POST /messages | < 100ms | 300 | 消息发送 |
| GET /messages/{id} | < 150ms | 200 | 历史消息 |
| WebSocket 连接 | < 100ms | 1000 | 实时连接 |

### 5.2 负载测试场景

#### 5.2.1 `test_load_nearby_discovery` (P1)

**目标**: 附近发现接口负载

**场景**:
- 1000 个在线用户
- 每个用户每 10 秒调用一次 resolve
- 每次扫描到 5-10 个设备

**期望**:
- 平均响应 < 200ms
- 95 分位数 < 500ms
- 错误率 < 0.1%

---

#### 5.2.2 `test_load_messaging` (P1)

**目标**: 消息系统负载

**场景**:
- 500 个并发 WebSocket 连接
- 每个连接每 5 秒发送 1 条消息
- 持续 5 分钟

**期望**:
- 消息投递率 100%
- 平均延迟 < 50ms
- 无消息丢失

---

#### 5.2.3 `test_load_temp_id_rotation` (P2)

**目标**: Temp ID 刷新负载

**场景**:
- 10000 个设备
- 每个设备每 5 分钟刷新一次 temp_id

**期望**:
- 平均响应 < 50ms
- 数据库无连接池耗尽

---

## 附录 A: 测试工具

### 推荐工具

| 类型 | 工具 | 用途 |
|------|------|------|
| 单元测试 | pytest | Python 测试框架 |
| HTTP 测试 | pytest + httpx/requests | REST API 测试 |
| WebSocket 测试 | pytest + websockets | WebSocket 测试 |
| 性能测试 | locust / k6 | 负载测试 |
| 数据库 | pytest-postgresql | 测试数据库 |
| Mock | unittest.mock | 服务 mock |

### 测试数据库

```sql
-- 测试时使用独立的测试数据库
-- 每个测试后清理数据或使用事务回滚

CREATE DATABASE notepassing_test;
```

### 测试配置

```python
# test_config.py
TEST_DATABASE_URL = "postgresql://localhost/notepassing_test"
REDIS_TEST_URL = "redis://localhost:6379/1"
```

---

## 附录 B: 测试清单速查

### P0 必测项（发布前必须通过）

- [ ] 设备初始化（新设备/已有设备）
- [ ] 临时 ID 生成与解析
- [ ] 附近设备发现
- [ ] Boost 触发条件
- [ ] 离开范围会话过期
- [ ] 好友间无限制聊天
- [ ] 陌生人 2 条消息限制
- [ ] 好友申请发送与接受
- [ ] 屏蔽阻断交互
- [ ] WebSocket 消息收发
- [ ] 已读回执
- [ ] 所有错误码正确返回

### P1 重要项（建议发布前通过）

- [ ] 匿名模式隐私过滤
- [ ] 好友申请冷却期
- [ ] 并发附近解析
- [ ] 并发消息发送
- [ ] 性能基准测试

### P2/P3 优化项（后续迭代）

- [ ] 大规模负载测试
- [ ] 长时间稳定性测试
- [ ] 故障恢复测试
