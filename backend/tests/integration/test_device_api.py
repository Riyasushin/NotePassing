"""
设备API集成测试 - 测试Device Router的实际端点
"""

import pytest
from unittest.mock import patch, AsyncMock


class TestDeviceAPI:
    """设备API测试类"""
    
    @pytest.mark.asyncio
    async def test_init_device_endpoint(self, async_client):
        """P0: 测试POST /device/init端点"""
        with patch("app.routers.device.DeviceService") as MockService:
            mock_service = AsyncMock()
            mock_service.init_device.return_value = {
                "device_id": "550e8400-e29b-41d4-a716-446655440001",
                "nickname": "测试用户",
                "is_new": True,
                "created_at": "2026-03-14T10:53:00Z"
            }
            MockService.return_value = mock_service
            
            response = await async_client.post("/api/v1/device/init", json={
                "device_id": "550e8400-e29b-41d4-a716-446655440001",
                "nickname": "测试用户",
                "tags": ["摄影"],
                "profile": "简介"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["is_new"] is True
    
    @pytest.mark.asyncio
    async def test_init_device_invalid_uuid(self, async_client):
        """P0: 测试无效UUID返回5001错误"""
        response = await async_client.post("/api/v1/device/init", json={
            "device_id": "invalid-uuid",
            "nickname": "测试用户"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 5001
    
    @pytest.mark.asyncio
    async def test_get_device_profile_endpoint(self, async_client):
        """P0: 测试GET /device/{device_id}端点"""
        with patch("app.routers.device.DeviceService") as MockService:
            mock_service = AsyncMock()
            mock_service.get_device_profile.return_value = {
                "device_id": "550e8400-e29b-41d4-a716-446655440002",
                "nickname": "目标用户",
                "avatar": "avatar.jpg",
                "tags": ["摄影"],
                "profile": "简介",
                "is_anonymous": False,
                "role_name": None,
                "is_friend": True
            }
            MockService.return_value = mock_service
            
            response = await async_client.get(
                "/api/v1/device/550e8400-e29b-41d4-a716-446655440002",
                params={"requester_id": "550e8400-e29b-41d4-a716-446655440001"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["nickname"] == "目标用户"
    
    @pytest.mark.asyncio
    async def test_update_device_endpoint(self, async_client):
        """P0: 测试PUT /device/{device_id}端点"""
        with patch("app.routers.device.DeviceService") as MockService:
            mock_service = AsyncMock()
            mock_service.update_device.return_value = {
                "device_id": "550e8400-e29b-41d4-a716-446655440001",
                "nickname": "新昵称",
                "avatar": "avatar.jpg",
                "tags": ["摄影"],
                "profile": "简介",
                "is_anonymous": False,
                "role_name": None,
                "updated_at": "2026-03-14T11:00:00Z"
            }
            MockService.return_value = mock_service
            
            response = await async_client.put(
                "/api/v1/device/550e8400-e29b-41d4-a716-446655440001",
                json={"nickname": "新昵称"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["nickname"] == "新昵称"
