"""Message schemas."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    """Send message request."""
    sender_id: str = Field(..., min_length=32, max_length=32)
    receiver_id: str = Field(..., min_length=32, max_length=32)
    content: str = Field(..., max_length=1000)
    type: str = Field(default="common", pattern="^(common|heartbeat)$")


class SendMessageResponse(BaseModel):
    """Send message response."""
    message_id: str
    session_id: str
    status: str
    created_at: datetime


class MessageHistoryItem(BaseModel):
    """Message item in history."""
    message_id: str
    sender_id: str
    content: str
    type: str
    status: str
    created_at: datetime


class MessageHistoryResponse(BaseModel):
    """Message history response."""
    session_id: str
    messages: List[MessageHistoryItem]
    has_more: bool


class MarkReadRequest(BaseModel):
    """Mark messages as read request."""
    device_id: str = Field(..., min_length=32, max_length=32)
    message_ids: List[str]


class MarkReadResponse(BaseModel):
    """Mark read response."""
    updated_count: int


class SyncMessageItem(BaseModel):
    """Message item in sync response (includes session_id and receiver_id)."""
    message_id: str
    session_id: str
    sender_id: str
    receiver_id: str
    content: str
    type: str
    status: str
    created_at: datetime


class SyncMessagesResponse(BaseModel):
    """Sync messages response."""
    messages: List[SyncMessageItem]
    has_more: bool
