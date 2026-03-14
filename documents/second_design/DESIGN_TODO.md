# 设计待办（Design TODO）

> 开发过程中发现的设计模糊点，需要产品决策后更新 unified_api_contract_v2.md。  
> 本文档按“从简单到复杂、从低耦合到高耦合”排序，目标是先减少返工，再补功能，再做体验。

---

## 建议优化流程（从简单到复杂）

1. **先统一现状认知**
   - TODO-4：修正接口路径和文档差异
   - TODO-5：把已经落地的消息补漏方案回写契约
   - 原因：这两项不先做，后续联调会持续出现“文档说 A，代码跑 B”

2. **再冻结匿名展示规则**
   - TODO-1：好友是否受匿名影响
   - TODO-2：陌生人匿名时显示 nickname 还是 role_name
   - 原因：附近页、Profile 页、好友申请弹窗、服务端隐私过滤都依赖这套规则

3. **然后补核心功能闭环**
   - TODO-6.1：加好友流程
   - TODO-6.2：查看 Profile
   - TODO-6.3：头像展示与上传
   - 原因：Repository 与 API 基础已在，适合顺着现有结构往前推

4. **最后做视觉统一**
   - TODO-3：主题、卡片、动画、头像组件
   - 原因：在规则和功能未冻结前做 UI 打磨最容易返工

---

## TODO-1：附近页好友的匿名展示逻辑

**场景**：用户 A 和用户 B 是好友。B 开启了匿名模式。A 在附近页扫到 B。

**问题**：A 的附近页卡片上，B 应该显示为：
- **(a)** 好友身份（显示真名 nickname + 头像 + 好友角标）—— 匿名对好友无效
- **(b)** 匿名身份（显示 role_name、隐藏头像）—— 附近页统一走匿名规则，不论是否好友

**当前代码现状**：
- Server `DeviceService.get_device()` 对好友返回完整资料
- Android 附近页已有好友角标，卡片主标题固定显示 `nickname`
- 因此当前实现天然更接近方案 (a)

**最小成本方案**：选方案 (a)
- 好友始终显示真实昵称 + 头像 + 好友角标
- 匿名模式只对陌生人生效

**为什么先这样做**：
- 与契约 `§0.5 隐私可见性规则` 一致
- 不需要为好友链路额外维护“匿名视图”和“真实视图”两套 UI
- 后续 Profile 页、好友页、聊天页都能复用同一显示规则

**如果坚持方案 (b)**：
- 需要同时改 nearby / chat / friends / profile 的显示逻辑
- 需要额外定义“好友但匿名”的所有可见性边界，返工范围更大

**状态**：🟡 建议锁定为方案 (a)，待同步到契约说明与客户端显示规则

---

## TODO-2：匿名模式下的名称展示策略

**场景**：用户 B 开启匿名模式，陌生人 A 在附近页看到 B。

**问题**：A 看到的卡片上显示什么名字？
- **(a)** 仍显示 B 的 nickname（当前 API `§0.5` 定义：nickname 对陌生人可见）
- **(b)** 显示 role_name 替代 nickname（MVP 描述的“神秘人”行为，真名隐藏）
- **(c)** 显示固定文案“神秘人”，role_name 作为副标题

**当前代码现状**：
- Server 当前对“陌生人 + 匿名”会隐藏 `avatar`，但仍返回 `nickname` 与 `role_name`
- Android 数据模型已接收 `is_anonymous` 和 `role_name`
- Android 附近页 UI 目前只使用 `nickname`，尚未真正显示匿名视图

**按复杂度拆分的两条路线**：

### 路线 A：最快闭环（低复杂度）
选方案 (a)
- 保持陌生人可见 `nickname`
- 匿名只影响头像与 `role_name` 展示
- 只需要补 NearbyCard 的匿名副文案或标签，不需要改服务端契约

### 路线 B：产品表达更强（中高复杂度）
选方案 (b)，并增加兜底：
- 陌生人匿名时主标题显示 `role_name`
- 若 `role_name` 为空，则兜底显示“神秘人”
- 同时隐藏头像
- 这更符合 MVP 中“显示身份还是神秘人”的产品语义

**推荐**：
- 若目标是最快把 Phase 9 闭环跑通：先走路线 A
- 若目标是强化产品辨识度：把路线 B 作为 TODO-6 之前的独立决策，一次性同步 Server + Contract + Android UI

**路线 B 的改动范围**：
- 修改 `unified_api_contract_v2.md` 的 `§0.5` 可见性说明
- 修改 Server `DeviceService.get_device()` 的返回策略，避免把真实 `nickname` 暴露给匿名陌生人
- 修改 NearbyCard / 未来 Profile 页 / 好友申请弹窗的主标题逻辑

**状态**：🟡 当前代码更接近方案 (a)；若改为方案 (b)，应作为一次独立的契约变更处理

---

## TODO-3：UI 风格统一调整

**当前代码现状**：
- 已有页面普遍使用 Material3 默认样式
- 卡片层已经有基础统一（圆角 16dp + `surfaceContainerLow`）
- 头像仍是图标占位
- 工程中尚未引入 Coil，头像远程加载还没开始

**建议不要现在直接做“大一统美化”**：
- 功能与显示规则还未冻结，尤其是 TODO-1 / TODO-2 / TODO-6
- 头像组件、Profile 页、好友申请入口都还会改变卡片布局

**更合理的拆法**：
1. 设计令牌层：颜色、圆角、间距、字体层级
2. 组件层：Avatar、NearbyCard、FriendCard、ProfileHeader
3. 体验层：过渡动画、Boost 高亮、空状态插画

**推荐时机**：
- 在 TODO-6.1 和 TODO-6.2 完成后再做
- 头像组件应等“展示方案”确定后再统一，不必等“上传方案”完成

**状态**：⏳ 保持低优先级，放在核心闭环后处理

---

## TODO-4：契约与实现差异

**当前代码现状（重要）**：
- Unified Contract 与 Backend Router 当前仍是 `/block`（单数）
- Android `RelationApi` 当前调用的是 `/blocks` 和 `/blocks/{target_device_id}`（复数）
- 所以“路径已修复”这句话目前不成立，联调仍有风险

**最小成本方案**：
- 直接把 Android 端改回 `/block` 和 `/block/{target_device_id}`
- 原因：Backend 与契约已经一致，只改 Android 成本最低

**更高成本方案**：
- 若团队更偏好 `/blocks` 复数命名
- 则需要同步修改 Backend Router + Unified Contract + 相关文档
- 这是一次完整接口变更，不应只改单边

**另一个差异：陌生人 profile 可见性**：
- Backend 当前 `DeviceService.get_device()` 会返回 `profile`
- Unified Contract 也写的是陌生人可见 `profile`
- 因此这里应以 Contract / 当前代码为准
- 服务器 README 中“Strangers (Public) 下 profile Hidden”更像旧说明，应视为过期

**状态**：⚠️ 路径差异未真正修复；隐私可见性以当前 Contract + Backend 实现为准

---

## TODO-5：消息握手机制（防丢消息）

**场景**：A 发送消息给 B，服务器成功保存并通过 WebSocket 推送 `new_message` 给 B，但 B 的 WS 连接不稳定（断连/重连中/后台被杀），导致推送丢失，B 永远看不到这条消息。

**当前代码现状**：
- Backend 已有 `GET /messages/sync`
- Backend `GET /messages/{session_id}` 已支持 `after` 参数
- Android `MessageRepository` 已实现全局同步和单会话同步
- Android `IncomingMessageHandler` 已在 WS 重连后自动触发全局补漏

**结论**：
- MVP 版本的方案 (b) “未送达消息拉取”已经落地
- 当前最需要做的不是再写一套 ACK，而是把契约和摘要文档同步到现状

**最小成本方案**：
- 更新 `unified_api_contract_v2.md`
- 明确写入 `/messages/sync`
- 明确 `GET /messages/{session_id}` 的 `after` 增量同步语义
- 在 `API_CHANGES_SUMMARY.md` 标记 TODO-5 的 MVP 方案已完成

**后续增强方案（更复杂）**：
- ACK 机制：适合后续做“已送达”与“真正已读”的区分
- 推送失败重试队列：适合多端、后台存活弱、消息一致性要求更高时引入

**推荐排序**：
- 先把文档补齐
- 再观察实际丢消息场景
- 只有现有拉取补漏仍不够时，才进入 ACK / retry 方案

**状态**：✅ MVP 方案已实现 / ⏳ 契约文档待补齐

---

## TODO-6：加好友 / 看 Profile / 传头像

**总原则**：
- 这一项不要一次性“大包并发开发”
- 最好拆成 6.1 → 6.2 → 6.3，前一项稳定再做后一项

### 6.1 加好友流程

**当前代码现状**：
- Android `RelationRepository` 已有 `sendFriendRequest()` / `respondFriendRequest()` / `syncFriends()`
- WebSocket 类型常量里已有 `friend_request`
- 但全局 WS 处理器还没有接住 `friend_request`
- 附近页 / 聊天页也还没有“加好友”按钮和请求弹窗

**最小成本方案**：
1. 附近页与聊天页加“加好友”入口
2. 发送前只做本地 `chat_history` 校验
3. App 级监听 `friend_request`，先用简单弹窗或 Snackbar 完成 accept / reject
4. 接受后调用 `syncFriends()`，本地刷新好友列表和会话信息

**复杂度**：中等  
**推荐优先级**：高

### 6.2 查看 Profile

**当前代码现状**：
- Android `DeviceRepository.getProfile()` 已存在
- 当前导航没有 Profile route，也没有 ProfileScreen

**最小成本方案**：
- 先做只读 Profile 页
- 从附近页卡片 / 好友页卡片 / 聊天页标题跳转进入
- 直接复用 `GET /device/{device_id}`，不依赖头像上传即可先落地

**前置条件**：
- 先冻结 TODO-1 / TODO-2，否则 Profile 页的标题、头像、匿名文案会反复改

**复杂度**：中等偏上  
**推荐优先级**：高，排在 6.1 之后

### 6.3 头像展示 / 上传

**当前代码现状**：
- 本地已有 `avatar` 字段，`syncProfile()` 也会上传 avatar URL
- 但 Android 还没引入 Coil
- 服务端也还没有头像上传接口，只支持传 URL 字符串

**按复杂度拆分**：
1. 最简单：先支持“展示头像 URL”
   - 引入 Coil
   - 所有头像位置支持 URL + 占位图回退
2. 中等：设置页先允许手动输入 avatar URL
   - 不改服务端接口
   - 适合 MVP 快速验证
3. 最复杂：新增上传接口
   - 需要后端存储策略、URL 返回、鉴权或清理策略
   - 这是独立子项目，不建议插在好友 / Profile 主链里

**推荐**：
- 先做“显示”，再做“上传”
- 上传方案不要阻塞加好友和 Profile 页面

**状态**：⏳ 建议拆成 6.1 / 6.2 / 6.3 递进推进

---

## 建议执行顺序

1. 先修 TODO-4：统一 `block` 路径，消除联调假象
2. 立即补 TODO-5 文档：把已实现的消息补漏方案写进契约
3. 锁定 TODO-1：好友始终显示真实信息
4. 为 TODO-2 选路线：
   - 快速闭环：保留陌生人 `nickname`
   - 强化匿名：改为 `role_name / 神秘人`，作为独立契约变更
5. 拆分推进 TODO-6：
   - 先加好友
   - 再 Profile
   - 最后头像展示与上传
6. 等以上都稳定后，再做 TODO-3 的 UI 统一
