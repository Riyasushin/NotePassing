# NotePassing Server 测试文档

## 测试结构

```
tests/
├── conftest.py              # 共享fixtures和配置
├── README.md               # 本文档
├── unit/                   # 单元测试
│   ├── test_device_service.py       # DeviceService测试 (11个测试)
│   ├── test_temp_id_service.py      # TempIdService测试 (9个测试)
│   ├── test_presence_service.py     # PresenceService测试 (10个测试)
│   ├── test_messaging_service.py    # MessagingService测试 (13个测试)
│   ├── test_relation_service.py     # RelationService测试 (16个测试)
│   └── test_websocket_manager.py    # WebSocketManager测试 (10个测试)
├── integration/            # 集成测试
│   ├── test_device_api.py           # Device API测试
│   ├── test_presence_api.py         # Presence API测试
│   ├── test_messaging_api.py        # Messaging API测试
│   └── test_friendship_api.py       # Friendship API测试
└── e2e/                    # 端到端测试
    ├── test_first_meeting.py        # 首次相遇场景
    ├── test_boost_reunion.py        # Boost重逢场景
    ├── test_temp_session_expire.py  # 会话过期场景
    └── test_block_interaction.py    # 屏蔽交互场景
```

## 运行测试

### 环境准备

```bash
# 安装依赖
uv sync --extra dev

# 运行数据库迁移
uv run alembic upgrade head
```

### 运行所有测试

```bash
uv run pytest
```

### 运行特定类别测试

```bash
# 单元测试
uv run pytest tests/unit/ -v

# 集成测试
uv run pytest tests/integration/ -v

# E2E测试
uv run pytest tests/e2e/ -v

# 按优先级
uv run pytest -m p0 -v
uv run pytest -m p1 -v
```

### 运行特定测试文件

```bash
uv run pytest tests/unit/test_device_service.py -v
uv run pytest tests/unit/test_messaging_service.py::TestMessagingService::test_send_message_stranger_first_two -v
```

### 覆盖率报告

```bash
uv run pytest --cov=app --cov-report=term-missing
uv run pytest --cov=app --cov-report=html
```

## 测试覆盖率

| 模块 | 覆盖率目标 | 状态 |
|------|----------|------|
| DeviceService | 90%+ | ✅ |
| TempIdService | 90%+ | ✅ |
| PresenceService | 90%+ | ✅ |
| MessagingService | 90%+ | ✅ |
| RelationService | 90%+ | ✅ |
| WebSocketManager | 85%+ | ✅ |
| 总体 | 85%+ | ✅ |

## 测试分类说明

### 单元测试

测试单个Service的业务逻辑，使用Mock数据库：

- **DeviceService**: 设备初始化、资料获取、更新、隐私过滤
- **TempIdService**: 临时ID生成、解析、过期处理
- **PresenceService**: 附近发现、Boost触发、距离计算
- **MessagingService**: 消息发送、历史查询、已读标记、2条限制
- **RelationService**: 好友申请、接受/拒绝、屏蔽、冷却期
- **WebSocketManager**: 连接管理、消息推送

### 集成测试

测试API端点的完整流程，验证请求-响应：

- **Device API**: /device/init, /device/{id}, PUT /device/{id}
- **Presence API**: /presence/resolve, /presence/disconnect
- **Messaging API**: /messages, /messages/{id}, /messages/read
- **Friendship API**: /friends, /friends/request, /block

### E2E测试

测试完整的用户场景：

- **首次相遇**: 陌生人→临时聊天→好友申请→成为好友
- **Boost重逢**: 好友接近→Boost触发→通知推送
- **会话过期**: 离开范围→临时会话过期→无法继续聊天
- **屏蔽交互**: 屏蔽→阻断所有交互→取消屏蔽→恢复

## 错误码测试覆盖

| 错误码 | 含义 | 测试状态 |
|--------|------|----------|
| 4001 | 临时聊天消息已达上限 | ✅ |
| 4002 | 临时会话已过期 | ✅ |
| 4003 | 不在蓝牙范围内 | N/A (客户端判断) |
| 4004 | 已被对方屏蔽 | ✅ |
| 4005 | 好友申请冷却中 | ✅ |
| 4006 | 无效的临时ID | ✅ |
| 4007 | 设备未初始化 | ✅ |
| 4008 | 好友关系不存在 | ✅ |
| 4009 | 重复操作 | ✅ |
| 5001 | 参数格式错误 | ✅ |
| 5002 | 服务器内部错误 | ✅ |

## 关键业务规则测试

### 陌生人消息限制 (2条规则)
- ✅ 前2条消息成功
- ✅ 第3条消息被阻止 (4001)
- ✅ 对方回复后可继续发送

### Boost触发条件
- ✅ 好友进入范围触发Boost
- ✅ 5分钟冷却期阻止重复触发
- ✅ 非好友不触发Boost

### 隐私规则
- ✅ 好友可见完整资料
- ✅ 陌生人匿名模式隐藏头像
- ✅ 陌生人匿名模式显示role_name

### 好友申请规则
- ✅ 24小时冷却期
- ✅ 已被屏蔽不能申请 (4004)
- ✅ 已有待处理申请不能重复申请 (4009)

### 会话过期规则
- ✅ 临时会话离开范围后过期
- ✅ 永久会话（好友）不过期

## 编写新测试

### 单元测试模板

```python
import pytest
from unittest.mock import MagicMock

class TestMyService:
    @pytest.fixture
    def service(self, mock_db):
        from app.services.my_service import MyService
        return MyService(mock_db)
    
    @pytest.mark.asyncio
    async def test_my_feature(self, service, mock_db):
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Act
        result = await service.my_method()
        
        # Assert
        assert result["code"] == 0
```

### 集成测试模板

```python
import pytest
from unittest.mock import patch, AsyncMock

class TestMyAPI:
    @pytest.mark.asyncio
    async def test_my_endpoint(self, async_client):
        with patch("app.routers.my_router.MyService") as MockService:
            mock_service = AsyncMock()
            mock_service.my_method.return_value = {"key": "value"}
            MockService.return_value = mock_service
            
            response = await async_client.post("/api/v1/my-endpoint", json={})
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
```

## 注意事项

1. **异步测试**: 所有Service方法都是异步的，使用`@pytest.mark.asyncio`
2. **数据库Mock**: 单元测试使用mock_db，不连接真实数据库
3. **WebSocket Mock**: WebSocket测试使用AsyncMock模拟
4. **错误处理**: 所有错误码都应被测试覆盖
5. **边界条件**: 长度限制、过期时间、冷却期等边界条件要测试
