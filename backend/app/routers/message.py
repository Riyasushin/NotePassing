"""
消息路由 - Messaging相关的API端点
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    SendMessageRequest,
    SendMessageResponse,
    GetMessagesResponse,
    MarkReadRequest,
    MarkReadResponse,
    BaseResponse,
)
from app.services import MessagingService, ws_manager
from app.exceptions import (
    ValidationError,
    DeviceNotInitializedError,
    FriendshipNotFoundError,
    BlockedError,
    TempMessageLimitError,
)

router = APIRouter()


@router.post("/messages", response_model=BaseResponse[SendMessageResponse])
async def send_message(
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    发送消息（HTTP备用通道）
    
    WebSocket不可用时的降级方案
    """
    service = MessagingService(db)
    try:
        result = await service.send_message(request)
        
        # WebSocket推送
        await ws_manager.send_new_message(
            device_id=request.receiver_id,
            message_id=result["message_id"],
            sender_id=request.sender_id,
            session_id=result["session_id"],
            content=request.content,
            msg_type=request.type,
            created_at=result["created_at"]
        )
        
        # 发送确认给发送者
        await ws_manager.send_message_sent(
            device_id=request.sender_id,
            message_id=result["message_id"],
            session_id=result["session_id"],
            created_at=result["created_at"]
        )
        
        return BaseResponse(data=result)
    except (
        ValidationError,
        DeviceNotInitializedError,
        BlockedError,
        TempMessageLimitError
    ) as e:
        return BaseResponse(code=e.code, message=e.message, data=None)


@router.get("/messages/{session_id}", response_model=BaseResponse[GetMessagesResponse])
async def get_message_history(
    session_id: str,
    device_id: str,
    before: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    获取历史消息
    
    支持分页，使用before游标
    """
    service = MessagingService(db)
    try:
        result = await service.get_message_history(
            session_id, device_id, before, limit
        )
        return BaseResponse(data=result)
    except (ValidationError, FriendshipNotFoundError) as e:
        return BaseResponse(code=e.code, message=e.message, data=None)


@router.post("/messages/read", response_model=BaseResponse[MarkReadResponse])
async def mark_messages_read(
    request: MarkReadRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    标记消息已读
    
    将指定消息标记为已读状态
    """
    service = MessagingService(db)
    try:
        result = await service.mark_messages_read(request)
        
        # WebSocket通知发送者
        if result["updated_count"] > 0:
            for sender_id in result.get("sender_ids", []):
                await ws_manager.send_messages_read(
                    device_id=sender_id,
                    message_ids=request.message_ids,
                    reader_id=request.device_id
                )
        
        return BaseResponse(data={"updated_count": result["updated_count"]})
    except ValidationError as e:
        return BaseResponse(code=e.code, message=e.message, data=None)
