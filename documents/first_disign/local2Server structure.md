# Local Data Structure（服务器接口对齐）

> 命名与字段定义与 [unified_api_contract.md](../unified_api_contract.md) 保持一致。

## 1. 附近发现（Presence）

| List | 更新方式 | 说明 |
|---|---|---|
| `ble_find` | BLE 扫描结果（每 5-10 秒刷新） | 本机直接扫描发现的设备 |
| `heartbeat_receive` | 收到 heartbeat 消息时更新 | 对方扫到我并通知我 |
| `chatable` | 实时计算 `ble_find ∪ heartbeat_receive` | 最终的"附近可聊天"列表。设备离开范围后 ≤1 分钟内仍可正常聊天；超过 1 分钟则临时会话过期，无法再发送消息 |

> heartbeat：解决 A 扫到 B 但 B 未扫到 A 的单向问题。A 通过服务器 message 通道（WebSocket `type: heartbeat`）向 ble_find 中所有对象发送 heartbeat（每 5 秒一次），B 收到后维护 heartbeat_receive，从而将 A 纳入 chatable。

## 2. 历史聊天（Chat History）

| List | 更新方式 | 说明 |
|---|---|---|
| `chat_history` | 设备进入 `chatable` 时自动追加 | 存储所有曾经进入过 `chatable` 的用户，**持久化存储，不会因离开范围而移除** |

**规则（参考 MVP_V2_0314）：**
- 用户首次进入 `chatable` 列表时，自动写入 `chat_history`
- `chat_history` 是附近页的数据来源：附近页显示所有 `chat_history` 中仍在 `chatable`（含 1 分钟失效态）的用户
- 好友申请的前提条件：对方存在于 `chat_history` 中（曾经或当前 chatable）——**此校验仅在客户端执行，服务端不检查**
- 持久化到 Room 数据库，随设备保留
- 卡片排序：chatable 好友 > chatable 非好友 > 失效好友 > 失效非好友；同级按蓝牙信号强度排序
- 卡片状态说明：
  - **chatable（有效态）**：在蓝牙范围内或离开 ≤1 分钟，仍可正常发送消息
  - **失效态**：离开蓝牙范围超过 1 分钟，临时会话过期，无法继续聊天（好友不受此限制）
- 被 `block` 的用户从所有列表中过滤，不在附近页显示

## 3. 好友（Relation）

| List | 更新方式 | 说明 |
|---|---|---|
| `friend` | 好友申请被接受后更新 | 双方互相同意好友申请后加入 |

每条好友记录本地额外维护：

| 字段 | 说明 |
|---|---|
| `meet_count` | 见面次数（每次 Boost 触发时 +1）。**仅本地计数，不与服务器同步** |
| `is_nearby` | 当前是否在蓝牙范围内（用于好友页 Boost 高亮） |

## 4. 屏蔽（Block）

| List | 更新方式 | 说明 |
|---|---|---|
| `block` | 本地屏蔽操作后更新 | 单方向屏蔽，屏蔽后对方从所有列表中过滤 |

## 5. 用户信息缓存（Device Profile Cache）

对所有涉及用户从服务器拉取并缓存（通过 `GET /api/v1/device/{device_id}` 或 `/presence/resolve` 返回值），定频更新：

`device_id` / `nickname` / `avatar` / `tags` / `profile` / `is_anonymous` / `role_name`
