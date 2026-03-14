"""
WebSocket Schema - WebSocket消息相关的Pydantic模型
"""

from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field


# ========== 客户端 -> 服务器 ==========

class WSClientSendMessage(BaseModel):
    """WebSocket发送消息请求"""
    action: Literal["send_message"]
    payload: dict


class WSClientMarkRead(BaseModel):
    """WebSocket标记已读请求"""
    action: Literal["mark_read"]
    payload: dict


class WSClientPing(BaseModel):
    """WebSocket心跳请求"""
    action: Literal["ping"]


# ========== 服务器 -> 客户端 ==========

class WSConnected(BaseModel):
    """连接成功消息"""
    type: Literal["connected"]
    payload: dict


class WSNewMessage(BaseModel):
    """新消息通知"""
    type: Literal["new_message"]
    payload: dict


class WSMessageSent(BaseModel):
    """消息发送确认"""
    type: Literal["message_sent"]
    payload: dict


class WSFriendRequest(BaseModel):
    """好友申请通知"""
    type: Literal["friend_request"]
    payload: dict


class WSFriendResponse(BaseModel):
    """好友申请结果通知"""
    type: Literal["friend_response"]
    payload: dict


class WSBoost(BaseModel):
    """Boost通知"""
    type: Literal["boost"]
    payload: dict


class WSSessionExpired(BaseModel):
    """会话过期通知"""
    type: Literal["session_expired"]
    payload: dict


class WSMessagesRead(BaseModel):
    """消息已读通知"""
    type: Literal["messages_read"]
    payload: dict


class WSPong(BaseModel):
    """心跳响应"""
    type: Literal["pong"]


class WSError(BaseModel):
    """错误通知"""
    type: Literal["error"]
    payload: dict
