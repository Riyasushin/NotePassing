# NotePassing

基于 BLE 发现的近距离匿名社交项目。蓝牙只负责发现附近设备，资料、消息、好友关系和屏蔽都通过服务器的 REST + WebSocket 传输。

## 仓库结构

- `android-app/`：Android 客户端，Kotlin + Compose + Room + BLE
- `backend/`：FastAPI 服务端，负责 profile / presence / relation / message
- `documents/`：设计文档、实施计划、开发规则
- `src/`：补充说明与代理文档

## 推荐阅读

1. `documents/third_design/README.md`
2. `documents/third_design/MVP_V3_0314.md`
3. `documents/third_design/unified_api_contract_v3.md`
4. `documents/third_design/DESIGN_TODO.md`
5. `documents/android_dev_plan.md`
6. `backend/README.md`

## 当前共识

- 三页结构：附近 / 好友 / 设置
- 核心闭环：发现 → 聊天 → 好友 → Boost
- `chatable` 由客户端维护：`ble_find ∪ heartbeat_receive`
- block 接口统一为 `/api/v1/block`
- 消息补漏统一为 `/api/v1/messages/sync` + `after`

## 开发边界

- Android 在本机编译运行
- Backend 部署在远程 Linux，本机不运行
- 路径、字段、WS type/action 以 `unified_api_contract_v3.md` 为准

