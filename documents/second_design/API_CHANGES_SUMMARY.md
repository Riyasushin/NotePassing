# NotePassing API V2 变更摘要

> 本文档汇总了从 V1 到 V2 的所有关键变更，供 Client 和 Server 开发者快速查阅。

---

## 🔴 关键变更（必看）

### 1. 心跳频率变更

| 项目 | V1 | V2 |
|------|-----|-----|
| 频率 | "约1Hz"（每秒1次） | **每 5 秒一次** |

**影响**: Client 需要调整心跳发送间隔。

---

### 2. Server 不管理在线状态 ❗

| 项目 | V1 | V2 |
|------|-----|-----|
| 在线状态 | Server 维护 `is_online` 字段 | **Client 自行判断，Server 不维护** |
| 离线检测 | Server 检测 | **Client 检测，通过 `presence/disconnect` 上报** |
| WebSocket 推送 | 判断在线状态后推送 | **始终推送，不判断在线状态** |

**Server 需要删除的逻辑**:
- [ ] 删除 `presence` 表的 `is_online` 字段
- [ ] 删除 Redis 在线状态管理
- [ ] 删除 WebSocket 连接状态检测（用于决定是否推送）

**Client 需要实现的逻辑**:
- [ ] 连续 6 次 BLE 扫描（约1分钟）未扫描到设备 → 视为离开范围
- [ ] 调用 `POST /api/v1/presence/disconnect` 上报
- [ ] 本地维护 `chatable` 列表（`ble_find ∪ heartbeat_receive`）

---

### 3. 错误码修正

| 错误码 | V1 | V2 |
|--------|-----|-----|
| 5002 | 设备不在线 | **服务器内部错误** |

---

## 🟡 字段命名统一

### 请求/响应字段

| 含义 | V1（旧/冲突） | V2（统一） |
|------|--------------|-----------|
| BLE 扫描结果 | `temp_ids` (Server_Design.md) | `scanned_devices` |
| Boost 提示列表 | `boost_triggered` (Server_Design.md) | `boost_alerts` |
| 距离估算 | `distance` (Server_Design.md) | `distance_estimate` |

---

## 🟡 消息类型统一

| 含义 | V1（冲突） | V2（统一） |
|------|-----------|-----------|
| 普通消息 | `text` (Server_Design.md) | `common` |
| 心跳消息 | `heartbeat` | `heartbeat` ✅ |

---

## 🟡 好友申请响应方式统一

| 方式 | V1（冲突） | V2（统一） |
|------|-----------|-----------|
| API 设计 | 独立端点：`/friends/:id/accept` 和 `/friends/:id/reject` | **单端点 + action 字段**：`PUT /friends/{request_id}` + `{"action": "accept"}` |

---

## 🟡 好友关系状态统一

| V1（冲突） | V2（统一） |
|-----------|-----------|
| `pending`, `accepted`, `rejected`, `blocked` (Server_ALL_API.md) | **`pending`, `accepted`, `rejected`** |
| `pending`, `accepted`, `blocked` (Server_Design.md) | （`blocked` 在独立 `blocks` 表） |

---

## 🟢 WebSocket 补充

### 新增 Server → Client 消息类型

#### 1. message_sent（消息发送确认）

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

#### 2. error（错误通知）

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

## 📋 检查清单

### Server 开发者

- [ ] 删除 `presence` 表的 `is_online` 字段
- [ ] 删除 Redis 在线状态相关代码
- [ ] 修正错误码 5002 为"服务器内部错误"
- [ ] 统一使用 `scanned_devices` 作为请求字段名
- [ ] 统一使用 `boost_alerts` 作为响应字段名
- [ ] 统一使用 `distance_estimate` 作为距离字段名
- [ ] 统一使用 `common` 作为普通消息类型
- [ ] 实现 `message_sent` WebSocket 响应
- [ ] 实现 `error` WebSocket 响应
- [ ] 好友申请响应使用 `action` 字段（非独立端点）

### Client 开发者

- [ ] 修改心跳发送频率为 **5秒一次**
- [ ] 实现离线判断逻辑（连续6次扫描未出现）
- [ ] 实现 `presence/disconnect` 上报
- [ ] 本地维护 `chatable` 列表（`ble_find ∪ heartbeat_receive`）
- [ ] 处理 `message_sent` WebSocket 消息
- [ ] 处理 `error` WebSocket 消息

---

## 📁 文件位置

- **完整契约文档**: `/second_design/unified_api_contract_v2.md`
- **变更摘要**: `/second_design/API_CHANGES_SUMMARY.md` (本文档)

---

## ⚠️ 废弃文档

以下文档的内容已不完全准确，仅供参考，不应作为开发依据：

- `Server_Design.md`（旧版设计，存在命名冲突）
- `Server_ALL_API.md`（旧版 API，存在字段冲突）

**唯一可信文档**: `unified_api_contract_v2.md`
