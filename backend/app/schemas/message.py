"""
消息 Schema - Messaging相关的Pydantic模型
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    sender_id: str = Field(..., description="发送者设备ID")
    receiver_id: str = Field(..., description="接收者设备ID")
    content: str = Field(..., min_length=1, max_length=1000, description="消息内容")
    type: str = Field(default="common", description="消息类型: common/heartbeat")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sender_id": "550e8400-e29b-41d4-a716-446655440001",
                "receiver_id": "550e8400-e29b-41d4-a716-446655440002",
                "content": "你好",
                "type": "common"
            }
        }
    )


class SendMessageResponse(BaseModel):
    """发送消息响应"""
    message_id: str
    session_id: str
    status: str
    created_at: str


class MessageItem(BaseModel):
    """消息项"""
    message_id: str
    sender_id: str
    content: str
    type: str
    status: str
    created_at: str


class GetMessagesResponse(BaseModel):
    """获取消息历史响应"""
    session_id: str
    messages: List[MessageItem]
    has_more: bool


class MarkReadRequest(BaseModel):
    """标记已读请求"""
    device_id: str = Field(..., description="设备ID")
    message_ids: List[str] = Field(..., description="消息ID列表")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "550e8400-e29b-41d4-a716-446655440001",
                "message_ids": ["msg-1", "msg-2"]
            }
        }
    )


class MarkReadResponse(BaseModel):
    """标记已读响应"""
    updated_count: int
