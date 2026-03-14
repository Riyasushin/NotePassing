"""Presence schemas."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ScannedDevice(BaseModel):
    """Scanned BLE device info."""
    temp_id: str = Field(..., min_length=32, max_length=32)
    rssi: int = Field(..., description="Signal strength in dBm")


class NearbyDevice(BaseModel):
    """Resolved nearby device info."""
    temp_id: str
    device_id: str
    nickname: str
    avatar: Optional[str] = None
    tags: List[str]
    profile: Optional[str] = None
    is_anonymous: bool
    role_name: Optional[str] = None
    distance_estimate: float = Field(..., description="Estimated distance in meters")
    is_friend: bool


class BoostAlert(BaseModel):
    """Boost alert for friend coming nearby."""
    device_id: str
    nickname: str
    distance_estimate: float


class PresenceResolveRequest(BaseModel):
    """Request to resolve scanned temp IDs."""
    device_id: str = Field(..., min_length=32, max_length=32)
    scanned_devices: List[ScannedDevice]


class PresenceResolveResponse(BaseModel):
    """Response with resolved nearby devices."""
    nearby_devices: List[NearbyDevice]
    boost_alerts: List[BoostAlert]


class PresenceDisconnectRequest(BaseModel):
    """Request to report device leaving range."""
    device_id: str = Field(..., min_length=32, max_length=32)
    left_device_id: str = Field(..., min_length=32, max_length=32)


class PresenceDisconnectResponse(BaseModel):
    """Response for disconnect report."""
    session_expired: bool
    session_id: Optional[str] = None
