"""
附近关系API集成测试 - 测试Presence Router的实际端点
"""

import pytest
from unittest.mock import patch, AsyncMock


class TestPresenceAPI:
    """附近关系API测试类"""
    
    @pytest.mark.asyncio
    async def test_resolve_nearby_endpoint(self, async_client):
        """P0: 测试POST /presence/resolve端点"""
        with patch("app.routers.presence.PresenceService") as MockService:
            mock_service = AsyncMock()
            mock_service.resolve_nearby_devices.return_value = {
                "nearby_devices": [
                    {
                        "temp_id": "temp123",
                        "device_id": "550e8400-e29b-41d4-a716-446655440002",
                        "nickname": "附近用户",
                        "distance_estimate": 2.5,
                        "is_friend": False
                    }
                ],
                "boost_alerts": []
            }
            MockService.return_value = mock_service
            
            response = await async_client.post("/api/v1/presence/resolve", json={
                "device_id": "550e8400-e29b-41d4-a716-446655440001",
                "scanned_devices": [
                    {"temp_id": "temp123", "rssi": -65}
                ]
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert len(data["data"]["nearby_devices"]) == 1
    
    @pytest.mark.asyncio
    async def test_resolve_nearby_with_boost(self, async_client):
        """P0: 测试附近解析返回Boost提醒"""
        with patch("app.routers.presence.PresenceService") as MockService:
            mock_service = AsyncMock()
            mock_service.resolve_nearby_devices.return_value = {
                "nearby_devices": [
                    {
                        "temp_id": "temp123",
                        "device_id": "550e8400-e29b-41d4-a716-446655440002",
                        "nickname": "好友",
                        "is_friend": True,
                        "distance_estimate": 1.5
                    }
                ],
                "boost_alerts": [
                    {
                        "device_id": "550e8400-e29b-41d4-a716-446655440002",
                        "nickname": "好友",
                        "distance_estimate": 1.5
                    }
                ]
            }
            MockService.return_value = mock_service
            
            response = await async_client.post("/api/v1/presence/resolve", json={
                "device_id": "550e8400-e29b-41d4-a716-446655440001",
                "scanned_devices": [
                    {"temp_id": "temp123", "rssi": -60}
                ]
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert len(data["data"]["boost_alerts"]) == 1
    
    @pytest.mark.asyncio
    async def test_report_disconnect_endpoint(self, async_client):
        """P0: 测试POST /presence/disconnect端点"""
        with patch("app.routers.presence.PresenceService") as MockService:
            mock_service = AsyncMock()
            mock_service.report_disconnect.return_value = {
                "session_expired": True,
                "session_id": "temp-sess-123"
            }
            MockService.return_value = mock_service
            
            response = await async_client.post("/api/v1/presence/disconnect", json={
                "device_id": "550e8400-e29b-41d4-a716-446655440001",
                "left_device_id": "550e8400-e29b-41d4-a716-446655440002"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["session_expired"] is True
