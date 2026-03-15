# NotePassing V3 Design TODO

> 只保留当前仍需决策或推进的事项。  
> 已经收口的结论不再展开写成长文。

## 已收口

- block 接口统一为 `/api/v1/block`
- 消息补漏统一为 `/api/v1/messages/sync` + `after`
- `third_design/` 作为当前默认文档源
- 设置页支持 tag 编辑并随资料同步上报
- Nearby 卡片显示 tag，不再显示 profile
- Nearby / Friends 支持点击头像查看资料详情弹窗
- tag 输入格式统一为 `#标签 #标签`，设置页自动补 `#`，并支持后台相同 tag 震动提醒

## 建议执行顺序

1. 先冻结匿名显示规则 ok
2. 再补加好友闭环 ok
2.5. 头像功能 ok
3. 然后上点击头像进入 Profile tag详情 页面 ok

5. 增加tag，并且优化显示在卡片上 ok
6. 相似tag震动提醒 ok
6. 改为显示蓝牙强度 ok

7. 后台优化，持续扫描+广播
4. 最后做头像展示与 UI 统一：去除测试功能、增加ui辨识度差异

7. codex网站demo实时显示蓝牙拓扑网络架构

- 加入tag重逢高亮特效
- 加入好友重逢 tag特效
产品设计：
app图标设计
导航页逻辑优化
附近聊天、好友卡片风格化
好友组件、block组件优化
设置页逻辑优化
加入网络显示功能？



## D1：好友是否受匿名影响

**默认方案**：好友始终显示真实昵称与头像。

原因：
- 与当前后端隐私过滤一致
- 与好友页 / 聊天页 / Profile 页更容易共用同一套规则
- 返工最小

## D2：陌生人匿名时显示什么名字】


### 方案 A

- 显示 `nickname`
- 隐藏头像
- `role_name` 作为附加信息

优点：改动最小，适合快速闭环。

### 方案 B

- 主标题显示 `role_name`
- `role_name` 为空时回退为“神秘人”
- 同时隐藏头像

优点：产品表达更强。  
代价：需要同时修改契约、服务端过滤和客户端显示逻辑。

**推荐**：若优先交付，先用方案 A；若优先强化匿名感，再单独做一次契约变更。

## F1：加好友流程

- 附近页 / 聊天页增加“加好友”入口
- 处理 WS `friend_request` / `friend_response`
- accept 后刷新本地 friends 与 session

## F2：Profile 页面

- 先做只读版本
- 入口来自 nearby / friends / chat
- 直接复用 `GET /device/{device_id}`

## F3：头像能力

### 阶段 1

- 引入 Coil
- 支持按 URL 展示头像

### 阶段 2

- 设置页支持手动填写 avatar URL

### 阶段 3

- 如确有必要，再补上传接口

## Later：UI 统一

- 统一颜色、圆角、间距、字体层级
- 抽 Avatar / NearbyCard / FriendCard / ProfileHeader 公共组件
- 最后再做动画和空状态
