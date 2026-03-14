# NotePassing V3 Design TODO

> 只保留当前仍需决策或推进的事项。  
> 已经收口的结论不再展开写成长文。

## 已收口

- block 接口统一为 `/api/v1/block`
- 消息补漏统一为 `/api/v1/messages/sync` + `after`
- `third_design/` 作为当前默认文档源

## 建议执行顺序

1. 先冻结匿名显示规则
2. 再补加好友闭环
3. 然后上 Profile 页面
4. 最后做头像展示与 UI 统一

## D1：好友是否受匿名影响

**默认方案**：好友始终显示真实昵称与头像。

原因：
- 与当前后端隐私过滤一致
- 与好友页 / 聊天页 / Profile 页更容易共用同一套规则
- 返工最小

## D2：陌生人匿名时显示什么名字

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
