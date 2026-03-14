# Local Data Structure（服务器接口对齐）

## 1. 附近发现

| List | 说明 |
|---|---|
| `ble_find` | BLE 扫描到的设备，定频更新 |
| `heartbeat_receive` | 收到的 heartbeat 消息，定频更新 |
| `chatable` | `ble_find ∪ heartbeat_receive`，实时计算 |

> heartbeat：解决 A 扫到 B 但 B 未扫到 A 的单向问题。A 通过服务器 message 通道向 ble_find 中所有对象发送 heartbeat（~1Hz），B 收到后维护 heartbeat_receive，从而将 A 纳入 chatable。

## 2. 好友

| List | 说明 |
|---|---|
| `friend` | 双方互相同意好友申请后加入 |

## 3. 拉黑

| List | 说明 |
|---|---|
| `block` | 单方向拉黑 |

## 4. 用户信息缓存

对所有涉及用户从服务器拉取并缓存，定频更新：

`user_id` / `nickname` / `avatar` / `tags` / `profile` / `is_anonymous`
