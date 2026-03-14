"""
Pytest配置和共享fixtures

提供测试所需的mock和fixtures
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

# 测试数据常量
TEST_DEVICE_ID_A = "550e8400-e29b-41d4-a716-446655440001"
TEST_DEVICE_ID_B = "550e8400-e29b-41d4-a716-446655440002"
TEST_DEVICE_ID_C = "550e8400-e29b-41d4-a716-446655440003"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    创建测试会话的事件循环
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db():
    """
    Mock数据库会话
    """
    mock = MagicMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.refresh = AsyncMock()
    return mock


@pytest.fixture
def sample_device_data():
    """
    示例设备A数据
    """
    return {
        "device_id": TEST_DEVICE_ID_A,
        "nickname": "测试用户A",
        "avatar": "https://example.com/avatar.jpg",
        "tags": ["摄影", "旅行"],
        "profile": "喜欢拍照和旅行",
        "is_anonymous": False,
        "role_name": None,
        "created_at": datetime.utcnow(),
        "updated_at": None,
    }


@pytest.fixture
def sample_device_data_b():
    """
    示例设备B数据
    """
    return {
        "device_id": TEST_DEVICE_ID_B,
        "nickname": "测试用户B",
        "avatar": "https://example.com/avatar_b.jpg",
        "tags": ["音乐"],
        "profile": "音乐爱好者",
        "is_anonymous": False,
        "role_name": None,
        "created_at": datetime.utcnow(),
        "updated_at": None,
    }


@pytest.fixture
def sample_temp_id():
    """
    示例临时ID数据
    """
    return {
        "temp_id": "a1b2c3d4e5f6789012345678abcdef01",
        "device_id": TEST_DEVICE_ID_A,
        "expires_at": datetime.utcnow() + timedelta(minutes=5),
    }


@pytest.fixture
def sample_scanned_devices():
    """
    示例BLE扫描设备
    """
    return [
        {"temp_id": "temp_id_1", "rssi": -65},
        {"temp_id": "temp_id_2", "rssi": -80},
    ]


@pytest.fixture
def mock_websocket():
    """
    Mock WebSocket连接
    """
    mock = AsyncMock()
    mock.accept = AsyncMock()
    mock.send_json = AsyncMock()
    mock.receive_json = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator:
    """
    异步HTTP测试客户端
    """
    from httpx import AsyncClient
    from app.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
