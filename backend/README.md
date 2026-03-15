# NotePassing API

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 基于蓝牙低功耗（BLE）的匿名附近消息传递后端 API，支持隐私优先的临时社交互动。

NotePassing 是一个保护隐私的消息后端服务，允许用户在不暴露身份的情况下发现并和附近的人聊天。用户通过 BLE 广播临时 ID，在彼此靠近时交换消息，并可通过好友系统建立持久连接。

---

## ✨ 特性

- **🔒 隐私优先设计** - 用户以设备 ID 标识，个人资料可见性可精细控制
- **📡 BLE 附近发现** - 使用临时广播 ID 扫描附近设备
- **💬 临时消息** - 无需添加好友即可与附近陌生人聊天
- **👥 好友系统** - 发送好友请求建立永久连接
- **⚡ 实时通信** - WebSocket 支持即时消息投递
- **🛡️ 隐私控制** - 支持匿名模式、屏蔽功能和细粒度的资料可见性

---

## 🏗️ 架构

### 技术栈

| 组件      | 技术                              |
| --------- | --------------------------------- |
| 框架      | FastAPI (异步)                    |
| 数据库    | PostgreSQL (生产) / SQLite (测试) |
| ORM       | SQLAlchemy 2.0 (异步)             |
| 迁移      | Alembic                           |
| WebSocket | FastAPI 原生 WebSocket            |
| 部署      | Docker + Docker Compose           |

### 数据模型

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  devices    │◄────┤  temp_ids   │     │   blocks    │
│  (用户)     │     │  (BLE ID)   │     │ (黑名单)    │
└──────┬──────┘     └─────────────┘     └─────────────┘
       │
       ├──► friendships (pending/accepted/rejected)
       │
       ├──► sessions ──► messages
       │
       └──► presences (附近追踪)
```

### 实体关系

| 实体                    | 说明                                                 |
| ----------------------- | ---------------------------------------------------- |
| **Device**              | 用户设备，存储昵称、头像、标签、个人简介等资料       |
| **TempID**              | 临时 BLE 广播 ID，10 分钟过期，防止长期追踪          |
| **Presence**            | 设备间附近关系记录，包含 RSSI 信号强度和最后见面时间 |
| **Session**             | 聊天会话，区分临时会话（非好友）和永久会话（好友）   |
| **Message**             | 聊天消息，支持普通消息和心跳消息                     |
| **Friendship**          | 好友关系，状态包括待处理、已接受、已拒绝             |
| **Block**               | 屏蔽关系，双向屏蔽后无法互动                         |
| **WebSocketConnection** | WebSocket 连接追踪                                   |

---

## 🚀 快速开始

### 前置要求

- Python 3.10+
- PostgreSQL 15+（或使用 Docker）
- Docker & Docker Compose（可选）

```bash
# 创建虚拟环境
uv sync
# 安装依赖
puv ip install -e ".[dev]"

# 设置环境变量
cp .env.example .env
# 编辑 .env 文件配置数据库连接

# 运行迁移
alembic upgrade head

# 使用提供的脚本启动（自动启动数据库和服务器）
./start.sh
```

[!Warning] 因为作者懒得做数据库持久化，所以（docker开数据库）docker关闭后数据就丢失了，需有需求请自行修改 `start.sh` 挂载数据卷（当然更建议vibe coding 一个 redis 作为 cache）

---

## 📚 API 概览

### REST 端点

#### 设备管理

| 端点                  | 方法 | 说明                       |
| --------------------- | ---- | -------------------------- |
| `/device/init`        | POST | 初始化或恢复设备           |
| `/device/{id}`        | GET  | 获取设备资料（带隐私过滤） |
| `/device/{id}`        | PUT  | 更新设备资料（部分更新）   |
| `/device/{id}/avatar` | POST | 上传头像图片               |

#### 临时 ID

| 端点               | 方法 | 说明                |
| ------------------ | ---- | ------------------- |
| `/temp-id/refresh` | POST | 生成新的临时 BLE ID |

#### 附近发现

| 端点                   | 方法 | 说明                           |
| ---------------------- | ---- | ------------------------------ |
| `/presence/resolve`    | POST | 解析扫描到的临时 ID 为设备资料 |
| `/presence/disconnect` | POST | 报告设备离开蓝牙范围           |

#### 好友系统

| 端点                          | 方法   | 说明                 |
| ----------------------------- | ------ | -------------------- |
| `/friends`                    | GET    | 获取好友列表         |
| `/friends/requests`           | GET    | 获取待处理的好友请求 |
| `/friends/request`            | POST   | 发送好友请求         |
| `/friends/{request_id}`       | PUT    | 接受/拒绝好友请求    |
| `/friends/{friend_device_id}` | DELETE | 删除好友             |

#### 消息系统

| 端点                     | 方法 | 说明                         |
| ------------------------ | ---- | ---------------------------- |
| `/messages`              | POST | 发送消息                     |
| `/messages/{session_id}` | GET  | 获取会话消息历史（支持分页） |
| `/messages/sync`         | GET  | 同步所有错过的消息           |
| `/messages/read`         | POST | 标记消息为已读               |

#### 屏蔽管理

| 端点                        | 方法   | 说明         |
| --------------------------- | ------ | ------------ |
| `/block`                    | POST   | 屏蔽用户     |
| `/block/{target_device_id}` | DELETE | 取消屏蔽用户 |

#### 系统端点

| 端点      | 方法 | 说明     |
| --------- | ---- | -------- |
| `/health` | GET  | 健康检查 |
| `/`       | GET  | 服务信息 |

### WebSocket 实时通信

连接地址: `/api/v1/ws?device_id={device_id}`

**客户端 → 服务器:**

- `send_message` - 发送消息
- `mark_read` - 标记消息已读
- `ping` - 保持连接活跃

**服务器 → 客户端:**

- `connected` - 连接确认
- `new_message` - 收到新消息
- `message_sent` - 消息发送确认
- `friend_request` - 收到好友请求
- `friend_response` - 好友请求响应
- `friend_deleted` - 被对方删除好友
- `boost` - 好友进入附近范围
- `session_expired` - 临时会话过期
- `messages_read` - 消息已读通知
- `error` - 错误通知

---

## 🔐 隐私与安全

### 临时 ID 生命周期

- 有效期 **10 分钟**（5 分钟活跃期 + 5 分钟缓冲期）
- 基于 `device_id` + `secret_key` + 时间戳 + 随机盐生成
- 自动轮换防止长期追踪

### 会话类型

| 类型         | 说明         | 限制                                             |
| ------------ | ------------ | ------------------------------------------------ |
| **临时会话** | 非好友间聊天 | 对方回复前最多发 2 条消息，蓝牙断开 1 分钟后过期 |
| **永久会话** | 好友间聊天   | 无限制                                           |

### 个人资料可见性

| 字段     | 好友    | 陌生人（匿名模式）                | 陌生人（公开模式） |
| -------- | ------- | --------------------------------- | ------------------ |
| 头像     | ✅ 可见 | ❌ 隐藏                           | ✅ 可见            |
| 昵称     | ✅ 可见 | ✅ 可见（显示"不愿透露姓名的ta"） | ✅ 可见            |
| 角色名   | ✅ 可见 | ❌ 隐藏                           | ❌ 隐藏            |
| 个人简介 | ✅ 可见 | ❌ 隐藏                           | ❌ 隐藏            |
| 标签     | ✅ 可见 | ❌ 隐藏                           | ✅ 可见            |

### 错误码

| 错误码 | 说明                     |
| ------ | ------------------------ |
| 0      | 成功                     |
| 4001   | 临时聊天消息已达上限     |
| 4002   | 临时会话已过期           |
| 4003   | 不在蓝牙范围内           |
| 4004   | 已被对方屏蔽             |
| 4005   | 好友申请冷却中（24小时） |
| 4006   | 无效的临时 ID            |
| 4007   | 设备未初始化             |
| 4008   | 好友关系不存在           |
| 4009   | 重复操作                 |
| 5001   | 参数格式错误             |
| 5002   | 服务器内部错误           |

---

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行并生成覆盖率报告
pytest --cov=app --cov-report=html

# 运行特定测试文件
pytest tests/test_device.py -v
pytest tests/test_message.py -v
pytest tests/test_websocket.py -v
```

---

## 📁 项目结构

```
.
├── app/                          # 主应用目录
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用入口
│   ├── config.py                 # 配置管理
│   ├── database.py               # 数据库连接与会话
│   ├── dependencies.py           # FastAPI 依赖
│   ├── models/                   # SQLAlchemy 数据模型
│   │   ├── device.py             # 设备模型
│   │   ├── temp_id.py            # 临时 ID 模型
│   │   ├── presence.py           # 附近关系模型
│   │   ├── session.py            # 会话模型
│   │   ├── message.py            # 消息模型
│   │   ├── friendship.py         # 好友关系模型
│   │   ├── block.py              # 屏蔽模型
│   │   └── ws_connection.py      # WebSocket 连接模型
│   ├── routers/                  # API 路由处理器
│   │   ├── device.py             # 设备路由
│   │   ├── temp_id.py            # 临时 ID 路由
│   │   ├── presence.py           # 附近发现路由
│   │   ├── friendship.py         # 好友路由
│   │   ├── message.py            # 消息路由
│   │   ├── block.py              # 屏蔽路由
│   │   └── websocket.py          # WebSocket 路由
│   ├── schemas/                  # Pydantic 请求/响应模型
│   │   ├── device.py
│   │   ├── temp_id.py
│   │   ├── presence.py
│   │   ├── friendship.py
│   │   ├── message.py
│   │   ├── block.py
│   │   ├── websocket.py
│   │   └── common.py
│   ├── services/                 # 业务逻辑层
│   │   ├── device_service.py     # 设备服务
│   │   ├── temp_id_service.py    # 临时 ID 服务
│   │   ├── presence_service.py   # 附近发现服务
│   │   ├── relation_service.py   # 好友/屏蔽关系服务
│   │   ├── message_service.py    # 消息服务
│   │   └── websocket_manager.py  # WebSocket 连接管理
│   └── utils/                    # 工具函数
│       ├── uuid_utils.py         # UUID 生成工具
│       ├── validators.py         # 参数验证
│       ├── exceptions.py         # 自定义异常
│       ├── error_codes.py        # 错误码定义
│       ├── response.py           # 响应封装
│       └── distance.py           # 距离估算（基于 RSSI）
├── tests/                        # 测试套件
│   ├── conftest.py               # pytest 配置和固件
│   ├── test_device.py            # 设备测试
│   ├── test_message.py           # 消息测试
│   ├── test_relation.py          # 关系测试
│   ├── test_temp_id.py           # 临时 ID 测试
│   ├── test_presence.py          # 附近发现测试
│   ├── test_websocket.py         # WebSocket 测试
│   └── test_integration.py       # 集成测试
├── alembic/                      # 数据库迁移
├── docker-compose.yml            # Docker 编排
├── Dockerfile                    # 容器定义
├── pyproject.toml                # 依赖和工具配置
├── .env.example                  # 环境变量示例
├── start.sh                      # 启动脚本
├── view_db.py                    # 数据库查看工具
└── README.md                     # 本文档
```

---

## ⚙️ 配置

环境变量（详见 `.env.example`）：

| 变量                     | 默认值                     | 说明                     |
| ------------------------ | -------------------------- | ------------------------ |
| `DATABASE_URL`           | `postgresql+asyncpg://...` | 数据库连接字符串         |
| `SECRET_KEY`             | `change-me-in-production`  | 临时 ID 生成密钥         |
| `DEBUG`                  | `true`                     | 调试模式开关             |
| `APP_NAME`               | `NotePassing API`          | 应用名称                 |
| `HOST`                   | `0.0.0.0`                  | 服务器监听地址           |
| `PORT`                   | `8000`                     | 服务器端口               |
| `PUBLIC_BASE_URL`        | `http://localhost:8000`    | 公开访问地址             |
| `TEMP_ID_EXPIRE_MINUTES` | `10`                       | 临时 ID 总有效期         |
| `TEMP_ID_BUFFER_MINUTES` | `5`                        | 刷新后的旧 ID 缓冲期     |
| `BOOST_COOLDOWN_MINUTES` | `5`                        | 好友进入附近提醒冷却时间 |

---

## 🛣️ 路线图

- [ ] 媒体消息支持（图片、语音）
- [ ] 端到端加密
- [ ] 附近用户群聊
- [ ] 地理围栏消息广播
- [ ] 推送通知（APNs/FCM）
- [ ] 消息持久化改进

---

## 🤝 贡献

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 📄 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

使用 [FastAPI](https://fastapi.tiangolo.com) 和 [SQLAlchemy](https://www.sqlalchemy.org/) 构建。
