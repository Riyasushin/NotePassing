"""WebSocket message schemas."""
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# Client -> Server messages
class WebSocketSendMessage(BaseModel):
    """Client sends a message."""
    action: Literal["send_message"]
    payload: dict


class WebSocketMarkRead(BaseModel):
    """Client marks messages as read."""
    action: Literal["mark_read"]
    payload: dict


class WebSocketPing(BaseModel):
    """Client ping."""
    action: Literal["ping"]


# Server -> Client messages
class WebSocketMessage(BaseModel):
    """Base WebSocket message."""
    type: str
    payload: dict


class WebSocketConnected(BaseModel):
    """Connection confirmation."""
    type: Literal["connected"]
    payload: dict


class WebSocketNewMessage(BaseModel):
    """New message notification."""
    type: Literal["new_message"]
    payload: dict


class WebSocketMessageSent(BaseModel):
    """Message sent confirmation."""
    type: Literal["message_sent"]
    payload: dict


class WebSocketFriendRequest(BaseModel):
    """Friend request notification."""
    type: Literal["friend_request"]
    payload: dict


class WebSocketFriendResponse(BaseModel):
    """Friend request response notification."""
    type: Literal["friend_response"]
    payload: dict


class WebSocketFriendDeleted(BaseModel):
    """Friendship removal notification."""
    type: Literal["friend_deleted"]
    payload: dict


class WebSocketBoost(BaseModel):
    """Boost notification for nearby friend."""
    type: Literal["boost"]
    payload: dict


class WebSocketSessionExpired(BaseModel):
    """Session expired notification."""
    type: Literal["session_expired"]
    payload: dict


class WebSocketMessagesRead(BaseModel):
    """Messages read notification."""
    type: Literal["messages_read"]
    payload: dict


class WebSocketError(BaseModel):
    """Error notification."""
    type: Literal["error"]
    payload: dict
