# Local Data Structure V2

> 与 [unified_api_contract_v2.md](./unified_api_contract_v2.md) 对齐。  
> 本文档仅描述 **客户端本地** 的数据结构、列表和行为逻辑，供 Local App 开发使用。

---

## 1. 本地列表总览

| 列表 | 存储方式 | 更新方式 | 说明 |
|------|----------|----------|------|
| `ble_find` | 内存 | BLE 扫描（每 5-10 秒） | 本机直接扫描到的设备 temp_id + rssi |
| `heartbeat_receive` | 内存 | 收到 WebSocket `type: heartbeat` 时写入 | 对方扫到我并通知我 |
| `chatable` | 内存 | 实时计算 `ble_find ∪ heartbeat_receive` | 当前附近可交互用户 |
| `chat_history` | Room（持久化） | 设备首次进入 `chatable` 时追加 | 所有曾经出现在附近的用户，永不自动删除 |
| `friend` | Room（持久化） | 好友申请被接受时写入 | 好友列表 |
| `block` | Room（持久化） | 用户执行屏蔽操作时写入 | 屏蔽列表，过滤一切交互 |

---

## 2. Presence（附近发现）

### 2.1 BLE 扫描 → `ble_find`

- 每 5-10 秒执行一次 BLE 扫描
- 结果为 `[{ temp_id, rssi }]`
- 上传 `POST /api/v1/presence/resolve`，服务器返回用户名片
- 用返回的 `nearby_devices` 刷新 `chatable`

### 2.2 Heartbeat → `heartbeat_receive`

- 解决单向发现问题（A 扫到 B 但 B 未扫到 A）
- A 向 `ble_find` 中所有设备发送 `type: heartbeat` 消息（WebSocket），**每 5 秒一次**
- B 收到后将 A 写入 `heartbeat_receive`
- 服务器仅透传 heartbeat，不做业务处理

### 2.3 `chatable` 计算

```
chatable = ble_find ∪ heartbeat_receive（过滤 block）
```

**状态机：**

| 状态 | 条件 | 可聊天 |
|------|------|--------|
| 有效（active） | 在 BLE 范围内或收到 heartbeat | ✓ |
| 宽限（grace） | 离开范围 ≤1 分钟 | ✓（非好友仍可发消息） |
| 失效（expired） | 离开范围 >1 分钟 | ✗（非好友临时会话过期；好友不受限） |

- 连续 ~6 次扫描未出现（约 1 分钟）→ 判定离开 → 调用 `POST /api/v1/presence/disconnect`
- Boost：好友从"不在附近"变为"在附近"时，`boost_alerts` 返回 → 触发震动 + UI 高亮

---

## 3. Chat History（历史记录）

- 用户首次进入 `chatable` 时自动写入 `chat_history`
- **持久化到 Room，不因离开范围而删除**
- 附近页数据源：`chat_history` 中仍在 `chatable`（含宽限态）的用户
- 好友申请前提：对方在 `chat_history` 中 → **仅客户端校验，服务端不检查**

---

## 4. Friend（好友）

- 好友申请通过后写入 `friend`
- 好友聊天不受距离和临时会话限制
- 同步来源：`GET /api/v1/friends`

**本地额外字段（不同步服务器）：**

| 字段 | 说明 |
|------|------|
| `meet_count` | Boost 触发时 +1，仅本地计数 |
| `is_nearby` | 当前是否在 `chatable` 中（好友页 Boost 高亮用） |

---

## 5. Block（屏蔽）

- 屏蔽后从 `chatable`、附近页、消息列表中过滤
- 同步到服务器：`POST /api/v1/block`
- 取消屏蔽：`DELETE /api/v1/block/{target_device_id}`

---

## 6. 用户信息缓存（Profile Cache）

缓存来源：`/presence/resolve` 响应 或 `GET /api/v1/device/{device_id}`

| 字段 | 说明 |
|------|------|
| `device_id` | 设备唯一 ID |
| `nickname` | 昵称 |
| `avatar` | 头像 URL（匿名陌生人不可见） |
| `tags` | 标签列表 |
| `profile` | 简介 |
| `is_anonymous` | 是否匿名 |
| `role_name` | 匿名角色名 |

---

## 7. 附近页卡片渲染规则

### 数据源

`chat_history` 中状态为 active / grace 的用户（过滤 `block`）

### 排序

1. active 好友（按 rssi 强→弱）
2. active 非好友（按 rssi 强→弱）
3. grace 好友（按离开时间短→长）
4. grace 非好友（按离开时间短→长）

### 卡片内容

| 项目 | active 态 | grace 态 |
|------|-----------|----------|
| 头像 | 显示 | 显示（半透明） |
| 昵称 | 显示 | 显示 |
| profile 摘要 | 显示 | 显示 |
| 上一条消息 | 显示 | 显示 |
| 距离 | `distance_estimate` | "已离开 Xs" |
| 好友申请按钮 | 可用 | 可用（仍在 chat_history） |

---

## 8. 网络层行为速查

| 场景 | 接口 | 频率/触发 |
|------|------|-----------|
| BLE 扫描结果上传 | `POST /presence/resolve` | 每 5-10 秒 |
| Heartbeat 发送 | WebSocket `send_message` type=heartbeat | 每 5 秒，向 ble_find 发送 |
| 设备离开通知 | `POST /presence/disconnect` | ~1 分钟未扫到时 |
| Temp ID 刷新 | `POST /temp-id/refresh` | 每 5 分钟，过期前 30 秒 |
| 发送消息 | WebSocket `send_message`（降级 `POST /messages`） | 用户触发 |
| 好友申请 | `POST /friends/request` | 用户触发 |
| 拉取好友列表 | `GET /friends` | 启动时 + 好友变更时 |
| 拉取历史消息 | `GET /messages/{session_id}` | 进入聊天页时 |
| 标记已读 | `POST /messages/read` 或 WebSocket `mark_read` | 阅读消息时 |
| WebSocket 保活 | `ping` / `pong` | 每 30 秒 |

---

## 9. 关键设计原则

- **Server 不管在线状态**：离线判断完全由客户端（BLE 扫描超时）负责
- **好友申请校验仅客户端做**：Server 只检查屏蔽、冷却、重复
- **见面次数仅本地统计**：`meet_count` 不上传服务器
- **Heartbeat 由服务器透传**：不做任何业务处理
- **消息优先走 WebSocket**：断线时降级为 HTTP POST
