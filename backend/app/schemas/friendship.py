"""Friendship schemas."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class FriendItem(BaseModel):
    """Friend item in list."""
    device_id: str
    nickname: str
    avatar: Optional[str] = None
    tags: List[str]
    profile: Optional[str] = None
    is_anonymous: bool
    last_chat_at: Optional[datetime] = None


class FriendListResponse(BaseModel):
    """Friend list response."""
    friends: List[FriendItem]


class FriendRequestRequest(BaseModel):
    """Send friend request."""
    sender_id: str = Field(..., min_length=32, max_length=32)
    receiver_id: str = Field(..., min_length=32, max_length=32)
    message: Optional[str] = Field(default=None, max_length=200)


class FriendRequestResponse(BaseModel):
    """Friend request response."""
    request_id: str
    status: str
    created_at: datetime


class FriendResponseRequest(BaseModel):
    """Respond to friend request."""
    device_id: str = Field(..., min_length=32, max_length=32)
    action: str = Field(..., pattern="^(accept|reject)$")


class FriendInfo(BaseModel):
    """Friend info in response."""
    device_id: str
    nickname: str
    avatar: Optional[str] = None


class FriendResponseResponse(BaseModel):
    """Friend response result."""
    request_id: str
    status: str
    friend: Optional[FriendInfo] = None
    session_id: Optional[str] = None
