"""Message router."""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from app.dependencies import DbDep
from app.schemas.message import (
    SendMessageRequest,
    SendMessageResponse,
    MessageHistoryResponse,
    MarkReadRequest,
    MarkReadResponse,
    SyncMessagesResponse,
)
from app.services.message_service import MessageService
from app.services.websocket_manager import push_new_message, push_message_sent
from app.utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["Messaging"])


@router.post("", response_model=dict)
async def send_message(
    data: SendMessageRequest,
    db: DbDep,
) -> dict:
    """
    Send a message to another device.
    
    - For friends: Messages are sent without restrictions
    - For non-friends: Temporary session is created automatically
      - Maximum 2 messages can be sent before receiving a reply
      - Session expires after Bluetooth disconnects for 1 minute
    
    Message types:
    - `common`: Regular text message
    - `heartbeat`: Presence notification for BLE range confirmation
    """
    result = await MessageService.send_message(db, data)

    message_payload = {
        "message_id": result.message_id,
        "sender_id": data.sender_id,
        "session_id": result.session_id,
        "content": data.content,
        "type": data.type,
        "created_at": result.created_at.isoformat(),
    }

    sent_to_receiver = await push_new_message(data.receiver_id, message_payload)
    logger.info(
        "WS push new_message to %s: %s",
        data.receiver_id,
        "delivered" if sent_to_receiver else "offline/not connected",
    )

    await push_message_sent(
        data.sender_id,
        {
            "message_id": result.message_id,
            "session_id": result.session_id,
            "status": result.status,
            "created_at": result.created_at.isoformat(),
        },
    )

    return success_response(data=result.model_dump())


@router.get("/sync", response_model=dict)
async def sync_messages(
    device_id: str,
    after: str = Query(..., description="ISO 8601 timestamp — get messages received after this time"),
    limit: int = Query(200, ge=1, le=500, description="Maximum messages to return"),
    db: DbDep = None,
) -> dict:
    """
    Sync all missed messages for a device.
    
    Returns messages where the device is the receiver and created_at > after.
    Used for catch-up after WebSocket reconnect.
    Heartbeat messages are excluded.
    """
    after_dt = datetime.fromisoformat(after.replace("Z", "+00:00"))
    result = await MessageService.sync_messages(db, device_id, after_dt, limit)
    return success_response(data=result.model_dump())


@router.get("/{session_id}", response_model=dict)
async def get_message_history(
    session_id: str,
    device_id: str,
    before: Optional[str] = Query(None, description="ISO 8601 timestamp for backward pagination"),
    after: Optional[str] = Query(None, description="ISO 8601 timestamp for forward sync"),
    limit: int = Query(20, ge=1, le=50, description="Number of messages to return"),
    db: DbDep = None,
) -> dict:
    """
    Get message history for a session.
    
    - Use `before` for backward pagination (older messages)
    - Use `after` for forward sync (newer messages since last known)
    - `before` and `after` are mutually exclusive; if both provided, `after` takes priority
    - Returns messages in chronological order (oldest first)
    - Maximum 50 messages per request
    """
    before_dt = None
    after_dt = None
    if after:
        after_dt = datetime.fromisoformat(after.replace("Z", "+00:00"))
    elif before:
        before_dt = datetime.fromisoformat(before.replace("Z", "+00:00"))
    
    result = await MessageService.get_history(
        db, session_id, device_id, before_dt, limit, after_dt
    )
    return success_response(data=result.model_dump())


@router.post("/read", response_model=dict)
async def mark_messages_read(
    data: MarkReadRequest,
    db: DbDep,
) -> dict:
    """
    Mark messages as read.
    
    - Only the receiver can mark messages as read
    - Updates status to "read" and sets read_at timestamp
    - Returns count of updated messages
    """
    result = await MessageService.mark_read(db, data)
    return success_response(data=result.model_dump())
