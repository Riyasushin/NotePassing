"""
好友关系 Schema - Friendship相关的Pydantic模型
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class FriendItem(BaseModel):
    """好友列表项"""
    device_id: str
    nickname: str
    avatar: Optional[str] = None
    tags: List[str] = []
    profile: str = ""
    is_anonymous: bool = False
    last_chat_at: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class GetFriendsResponse(BaseModel):
    """获取好友列表响应"""
    friends: List[FriendItem]


class SendFriendRequest(BaseModel):
    """发送好友申请请求"""
    sender_id: str = Field(..., description="申请者设备ID")
    receiver_id: str = Field(..., description="目标设备ID")
    message: Optional[str] = Field(None, max_length=200, description="验证消息")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sender_id": "550e8400-e29b-41d4-a716-446655440001",
                "receiver_id": "550e8400-e29b-41d4-a716-446655440002",
                "message": "想加你为好友"
            }
        }
    )


class SendFriendRequestResponse(BaseModel):
    """发送好友申请响应"""
    request_id: str
    status: str
    created_at: str


class RespondFriendRequest(BaseModel):
    """回应好友申请请求"""
    device_id: str = Field(..., description="操作者设备ID")
    action: str = Field(..., description="操作: accept/reject")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "550e8400-e29b-41d4-a716-446655440002",
                "action": "accept"
            }
        }
    )


class FriendInfo(BaseModel):
    """好友信息"""
    device_id: str
    nickname: str
    avatar: Optional[str] = None


class AcceptFriendResponse(BaseModel):
    """接受好友申请响应"""
    request_id: str
    status: str
    friend: FriendInfo
    session_id: str


class RejectFriendResponse(BaseModel):
    """拒绝好友申请响应"""
    request_id: str
    status: str


class BlockUserRequest(BaseModel):
    """屏蔽用户请求"""
    device_id: str = Field(..., description="操作者设备ID")
    target_id: str = Field(..., description="目标设备ID")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "550e8400-e29b-41d4-a716-446655440001",
                "target_id": "550e8400-e29b-41d4-a716-446655440002"
            }
        }
    )
