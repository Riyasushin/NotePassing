"""Device schemas."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# Base schemas
class DeviceBase(BaseModel):
    """Base device schema."""
    nickname: str = Field(..., max_length=50)
    tags: List[str] = Field(default_factory=list)
    profile: Optional[str] = Field(default=None, max_length=200)


# Request schemas
class DeviceInitRequest(BaseModel):
    """Device initialization request."""
    device_id: str = Field(..., min_length=32, max_length=32, description="UUID v4 without dashes")
    nickname: str = Field(..., max_length=50)
    tags: List[str] = Field(default_factory=list)
    profile: Optional[str] = Field(default=None, max_length=200)


class DeviceUpdateRequest(BaseModel):
    """Device profile update request (partial update)."""
    nickname: Optional[str] = Field(default=None, max_length=50)
    avatar: Optional[str] = Field(default=None, max_length=500)
    tags: Optional[List[str]] = None
    profile: Optional[str] = Field(default=None, max_length=200)
    is_anonymous: Optional[bool] = None
    role_name: Optional[str] = Field(default=None, max_length=50)


# Response schemas
class DeviceInitResponse(BaseModel):
    """Device initialization response."""
    device_id: str
    nickname: str
    is_new: bool
    created_at: datetime


class DeviceProfileResponse(BaseModel):
    """Device profile response with privacy filtering."""
    device_id: str
    nickname: str
    avatar: Optional[str] = None
    tags: List[str]
    profile: Optional[str] = None
    is_anonymous: bool
    role_name: Optional[str] = None
    is_friend: bool


class AvatarUploadResponse(BaseModel):
    """Avatar upload result."""
    avatar_url: str
    updated_at: datetime
