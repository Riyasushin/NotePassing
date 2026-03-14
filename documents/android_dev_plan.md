# NotePassing Android 开发计划

> 基于 second_design V2 设计文档，从框架到细节，逐模块推进。  
> 每个 Phase 完成后可独立编译运行验证。

---

## Phase 1：工程基础与项目骨架

**目标**：搭好包结构、引入依赖、跑通三页底部导航。

- [ ] 1.1 创建包结构
  ```
  com.example.notepassingapp/
  ├── ui/
  │   ├── theme/          # 已有
  │   ├── navigation/     # 导航框架
  │   ├── nearby/         # 附近页
  │   ├── friends/        # 好友页
  │   └── settings/       # 设置页
  ├── data/
  │   ├── local/          # Room 数据库
  │   │   ├── entity/     # 实体类
  │   │   ├── dao/        # DAO 接口
  │   │   └── database/   # Database 类
  │   └── model/          # 公共数据模型
  ├── repository/         # Repository 层
  └── util/               # 工具类
  ```
- [ ] 1.2 引入依赖：Navigation Compose、Room、Lifecycle ViewModel
- [ ] 1.3 实现底部导航栏（附近页 / 好友页 / 设置页三个 Tab）
- [ ] 1.4 三个页面放占位内容，确认导航切换正常

**验证**：编译运行，三个 Tab 可以点击切换，每页显示不同占位文字。

---

## Phase 2：数据层 — Room 数据库 + 本地身份

**目标**：定义所有本地持久化实体，跑通数据库；实现 device_id 生成。

- [ ] 2.1 定义 Room Entity
  - `ChatHistoryEntity`：device_id, nickname, avatar, tags, profile, is_anonymous, role_name, first_seen_at, last_seen_at, last_message, last_message_at, rssi, is_friend, state(active/grace/expired)
  - `FriendEntity`：device_id, nickname, avatar, tags, profile, session_id, meet_count, is_nearby, last_chat_at, created_at
  - `BlockEntity`：device_id, blocked_at
  - `MessageEntity`：message_id, session_id, sender_id, receiver_id, content, type, status(sent/read), created_at, read_at
  - `ProfileCacheEntity`：device_id, nickname, avatar, tags, profile, is_anonymous, role_name, updated_at

- [ ] 2.2 定义 DAO 接口
  - `ChatHistoryDao`：insert, update, getAll, getByDeviceId, getChatable, delete
  - `FriendDao`：insert, update, getAll, getByDeviceId, delete
  - `BlockDao`：insert, getAll, isBlocked, delete
  - `MessageDao`：insert, getBySession, getLatestBySession, markRead
  - `ProfileCacheDao`：insertOrUpdate, getByDeviceId

- [ ] 2.3 创建 `AppDatabase` 类
- [ ] 2.4 device_id 管理：首次启动生成 UUID v4 → SharedPreferences 持久化
- [ ] 2.5 创建 `DeviceManager` 工具类（读写 device_id、nickname 等本地配置）

**验证**：App 启动后自动生成 device_id 并持久化，重启不变。

---

## Phase 3：设置页（最简单的完整页面）

**目标**：实现设置页 UI + 首次启动引导流程。

- [ ] 3.1 首次启动引导页（Onboarding）
  - 输入昵称（必填）
  - 可选：头像、简介、标签
  - 点击"开始"→ 生成 device_id → 进入主页
- [ ] 3.2 设置页 UI
  - 显示当前头像、昵称、简介、标签
  - 编辑昵称、简介
  - 匿名模式开关（开启后显示 role_name 输入）
  - 标签编辑
- [ ] 3.3 SettingsViewModel
  - 读取/保存本地配置
  - 管理 UI 状态

**验证**：首次启动显示引导页，填写后进入主页；设置页可编辑并持久化。

---

## Phase 4：好友页

**目标**：好友列表展示 + 好友卡片 UI。

- [ ] 4.1 好友页 UI
  - 好友列表（LazyColumn）
  - 空状态提示（"还没有好友"）
- [ ] 4.2 好友卡片组件
  - 头像、昵称、简介摘要
  - 见面次数（meet_count）
  - 当前是否附近（is_nearby → Boost 高亮）
  - 最后聊天时间
- [ ] 4.3 FriendsViewModel
  - 从 Room 读取好友列表
  - 按 last_chat_at 排序
- [ ] 4.4 点击好友卡片 → 进入聊天页（Phase 6 实现，此处先占位）

**验证**：好友页显示本地数据库中的好友列表（可手动插入测试数据验证）。

---

## Phase 5：附近页 — 卡片列表

**目标**：附近页 UI 框架 + 卡片渲染 + 排序逻辑。

- [ ] 5.1 附近页 UI
  - 用户卡片列表（LazyColumn）
  - 空状态（"附近暂无用户"）
- [ ] 5.2 用户卡片组件（两种状态）
  - **active 态**：头像、昵称、profile 摘要、上一条消息、距离
  - **grace 态**：半透明头像、"已离开 Xs"
  - 好友标识角标
- [ ] 5.3 卡片排序逻辑
  1. active 好友（rssi 强→弱）
  2. active 非好友（rssi 强→弱）
  3. grace 好友（离开时间短→长）
  4. grace 非好友（离开时间短→长）
- [ ] 5.4 NearbyViewModel
  - 从 chat_history 读取 active/grace 用户
  - 过滤 block 列表
  - 执行排序
- [ ] 5.5 好友申请按钮（UI 占位，逻辑 Phase 7+）

**验证**：附近页按正确排序渲染卡片（用模拟数据测试）。

---

## Phase 6：聊天模块

**目标**：聊天界面 UI + 本地消息存储。

- [ ] 6.1 聊天页 UI
  - 顶部栏：对方昵称 + 返回按钮
  - 消息列表（LazyColumn，自动滚到底部）
  - 底部输入框 + 发送按钮
- [ ] 6.2 消息气泡组件
  - 发送方（右侧蓝色）/ 接收方（左侧灰色）
  - 时间戳
  - 已读/未读状态
- [ ] 6.3 ChatViewModel
  - 从 Room 加载历史消息
  - 发送消息（先存本地，后续接网络）
  - 非好友限制：未回复前最多 2 条
- [ ] 6.4 从附近页/好友页点击卡片进入聊天页（路由打通）

**验证**：点击卡片进入聊天页，可输入消息并本地显示。

---

## Phase 7：网络层

**目标**：接通服务器 REST API + WebSocket。

- [x] 7.1 引入依赖：Retrofit 2.11.0、OkHttp 4.12.0、Gson
- [x] 7.2 定义 API Service 接口（5 个 Service，15 个端点）+ DTO 数据类
- [x] 7.3 WebSocket 消息类型定义（WsMessage + WsPayloads）
- [x] 7.4 WebSocketManager（连接/断线重连/ping 保活/消息分发）
- [x] 7.5 Repository 层
  - `DeviceRepository`：init + syncProfile + getProfile
  - `TempIdRepository`：refresh + 缓存当前 temp_id
  - `PresenceRepository`：resolveNearby + reportDisconnect
  - `MessageRepository`：WS 优先发送，HTTP 降级，本地 Room 同步
  - `RelationRepository`：syncFriends + sendRequest + respond + block/unblock
- [x] 7.6 启动时调用 `POST /device/init` + WS 连接 + 好友同步
- [x] 7.7 设置页保存时调用 `PUT /device/{device_id}`
- [x] 7.8 聊天消息走网络（WS 优先，HTTP 降级）+ 监听 WS 推送入库

**Phase 7 全部完成** ✅（2026-03-14）
**待联调**：填入实际 `NetworkConfig.BASE_URL` / `WS_URL` 后即可联调。

---

## Phase 8：BLE 蓝牙模块

**目标**：实现 BLE 广播 + 扫描，发现附近设备。

- [x] 8.1 权限声明与运行时请求
  - AndroidManifest: BLUETOOTH_SCAN/ADVERTISE/CONNECT, LOCATION, FOREGROUND_SERVICE
  - NearbyScreen: 运行时权限请求 UI
- [x] 8.2 BLE Advertiser（广播端）
  - 广播 temp_id（从服务器获取）→ Service UUID + Service Data
  - BleForegroundService 前台服务保活
- [x] 8.3 BLE Scanner（扫描端）
  - 4 秒扫描 + 4 秒间隔循环
  - 结果写入内存 `bleFindMap`
- [x] 8.4 Temp ID 管理
  - BleManager 启动时调用 `POST /temp-id/refresh` 获取
  - 过期前 30 秒自动刷新
- [x] 8.5 扫描结果上传
  - 每轮扫描后调用 `POST /presence/resolve`
  - 用返回的 nearby_devices 更新 chat_history + _realtimeStates
  - NearbyViewModel 自动刷新附近页

**Phase 8 全部完成** ✅（2026-03-14）
**验证**：需两台手机互相 BLE 发现 → 附近页显示对方卡片。

---

## Phase 9：业务逻辑整合

**目标**：打通核心业务闭环。

- [ ] 9.1 chatable 状态机
  - `ble_find ∪ heartbeat_receive`（过滤 block）
  - active → grace（离开 ≤1 分钟）→ expired（>1 分钟）
- [ ] 9.2 Heartbeat 机制
  - 每 5 秒向 ble_find 中所有设备发送 type=heartbeat
  - 收到 heartbeat 写入 heartbeat_receive
- [ ] 9.3 离线检测
  - 连续 6 次扫描（约 1 分钟）未出现 → 视为离开
  - 调用 `POST /presence/disconnect`
  - 清理 chatable
- [ ] 9.4 好友申请流程
  - 发送申请（客户端校验 chat_history）
  - 接收申请弹窗
  - 接受/拒绝 → 更新本地好友列表
- [ ] 9.5 Boost 功能
  - 好友从"不在附近"变为"在附近" → 震动 + UI 高亮
  - meet_count +1
- [ ] 9.6 屏蔽功能
  - 屏蔽/取消屏蔽
  - 屏蔽后从所有列表过滤
- [ ] 9.7 临时会话管理
  - 非好友最多 2 条消息限制
  - 离开 1 分钟会话过期

**验证**：完整闭环——发现 → 聊天 → 加好友 → Boost → 屏蔽，全部可用。

---

## Phase 10：打磨与优化

**目标**：用户体验与稳定性。

- [ ] 10.1 加载状态 & 骨架屏
- [ ] 10.2 网络错误处理 & 重试
- [ ] 10.3 权限被拒引导
- [ ] 10.4 UI 动画（卡片出现/消失、页面切换）
- [ ] 10.5 通知（好友申请、新消息、Boost）
- [ ] 10.6 后台保活策略（前台服务 + WorkManager）
- [ ] 10.7 数据清理（过期 profile cache 等）
- [ ] 10.8 深色模式适配

---

## 依赖清单

| 功能 | 库 |
|------|-----|
| UI | Jetpack Compose + Material3 |
| 导航 | Navigation Compose |
| 本地存储 | Room |
| 配置存储 | DataStore / SharedPreferences |
| 网络 HTTP | Retrofit + OkHttp |
| 网络 WebSocket | OkHttp WebSocket |
| JSON | Gson / Moshi |
| 异步 | Kotlin Coroutines + Flow |
| 生命周期 | Lifecycle ViewModel |
| BLE | Android BLE API |
| 权限 | Accompanist Permissions |
| 图片 | Coil Compose |

---

## 当前进度

- [x] Android Studio 工程创建
- [x] 手机调试环境跑通
- [ ] **→ Phase 1 开始**
