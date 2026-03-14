# NotePassing Third Design

> `third_design/` 是当前默认设计入口。  
> 若与 `second_design/` 或旧版 README 冲突，以本目录为准。

## 阅读顺序

1. `MVP_V3_0314.md`
   - 产品目标、三页结构、核心规则
2. `unified_api_contract_v3.md`
   - 当前 REST / WebSocket 契约
3. `DESIGN_TODO.md`
   - 未决设计项与执行顺序
4. `../android_dev_plan.md`
   - Android 侧实施拆解

## 当前共识

- 蓝牙只负责发现附近设备
- 用户资料、消息、好友关系、屏蔽全部走服务器
- `chatable` 由客户端维护：`ble_find ∪ heartbeat_receive`
- block 接口统一为 `/api/v1/block`
- 消息补漏统一为 `/api/v1/messages/sync` + `after`

## 编辑原则

- 产品规则写进 `MVP_V3_0314.md`
- 接口定义只写进 `unified_api_contract_v3.md`
- 未决项只留在 `DESIGN_TODO.md`
- 避免跨文件重复粘贴大段内容