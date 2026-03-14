"""
附近关系 Schema - Presence相关的Pydantic模型
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ScannedDevice(BaseModel):
    """扫描到的设备"""
    temp_id: str = Field(..., description="临时ID")
    rssi: int = Field(..., description="信号强度 (dBm)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "temp_id": "a1b2c3d4e5f6789012345678abcdef01",
                "rssi": -65
            }
        }
    )


class PresenceResolveRequest(BaseModel):
    """附近设备解析请求"""
    device_id: str = Field(..., description="自身设备ID")
    scanned_devices: List[ScannedDevice] = Field(..., description="扫描到的设备列表")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "550e8400-e29b-41d4-a716-446655440001",
                "scanned_devices": [
                    {"temp_id": "abc123...", "rssi": -65},
                    {"temp_id": "789xyz...", "rssi": -80}
                ]
            }
        }
    )


class NearbyDevice(BaseModel):
    """附近设备信息"""
    temp_id: str
    device_id: str
    nickname: str
    avatar: Optional[str] = None
    tags: List[str] = []
    profile: str = ""
    is_anonymous: bool = False
    role_name: Optional[str] = None
    distance_estimate: float = Field(..., description="估算距离 (米)")
    is_friend: bool = False


class BoostAlert(BaseModel):
    """Boost提醒"""
    device_id: str
    nickname: str
    distance_estimate: float


class PresenceResolveResponse(BaseModel):
    """附近设备解析响应"""
    nearby_devices: List[NearbyDevice]
    boost_alerts: List[BoostAlert]


class PresenceDisconnectRequest(BaseModel):
    """离开范围上报请求"""
    device_id: str = Field(..., description="自身设备ID")
    left_device_id: str = Field(..., description="离开范围的设备ID")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "550e8400-e29b-41d4-a716-446655440001",
                "left_device_id": "550e8400-e29b-41d4-a716-446655440002"
            }
        }
    )


class PresenceDisconnectResponse(BaseModel):
    """离开范围上报响应"""
    session_expired: bool = Field(..., description="是否有临时会话过期")
    session_id: Optional[str] = Field(None, description="过期的会话ID")
