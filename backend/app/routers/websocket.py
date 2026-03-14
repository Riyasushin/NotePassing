"""WebSocket router."""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.services.websocket_manager import manager, push_error
from app.services.message_service import MessageService
from app.services.relation_service import RelationService
from app.schemas.message import SendMessageRequest, MarkReadRequest
from app.utils.validators import validate_device_id
from app.utils.exceptions import NotePassingException

router = APIRouter()


@router.websocket("/api/v1/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    device_id: str = Query(..., min_length=32, max_length=32),
):
    """
    WebSocket endpoint for real-time communication.
    
    Query Parameters:
        device_id: Device ID for connection identification
    
    Client -> Server Actions:
        - send_message: Send a message to another device
        - mark_read: Mark messages as read
        - ping: Keep connection alive
    
    Server -> Client Events:
        - connected: Connection confirmation
        - new_message: New message received
        - message_sent: Message sent confirmation
        - friend_request: Friend request received
        - friend_response: Friend request response
        - messages_read: Messages marked as read
        - error: Error notification
    """
    try:
        validate_device_id(device_id)
    except Exception:
        await websocket.close(code=4001, reason="Invalid device_id")
        return
    
    # Accept connection
    connection_id = await manager.connect(device_id, websocket)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            # Parse action
            action = data.get("action")
            payload = data.get("payload", {})
            
            if action == "ping":
                # Ping-pong for connection keepalive
                await websocket.send_json({"type": "pong"})
            
            elif action == "send_message":
                # Handle send message
                await handle_send_message(device_id, payload)
            
            elif action == "mark_read":
                # Handle mark read
                await handle_mark_read(device_id, payload)
            
            else:
                # Unknown action
                await push_error(
                    device_id,
                    5001,
                    f"Unknown action: {action}"
                )
    
    except WebSocketDisconnect:
        manager.disconnect(device_id)
    except Exception as e:
        # Handle unexpected errors
        try:
            await push_error(device_id, 5002, "Internal server error")
            await websocket.close(code=1011, reason="Server error")
        except Exception:
            pass
        manager.disconnect(device_id)


async def handle_send_message(sender_id: str, payload: dict):
    """Handle send_message action from WebSocket."""
    from app.services.websocket_manager import push_new_message, push_message_sent
    from app.database import AsyncSessionLocal
    
    try:
        # Create database session
        async with AsyncSessionLocal() as db:
            # Build request
            request = SendMessageRequest(
                sender_id=sender_id,
                receiver_id=payload.get("receiver_id"),
                content=payload.get("content"),
                type=payload.get("type", "common"),
            )
            
            # Send message
            result = await MessageService.send_message(db, request)
            
            # Confirm to sender
            await push_message_sent(
                sender_id,
                {
                    "message_id": result.message_id,
                    "session_id": result.session_id,
                    "status": result.status,
                    "created_at": result.created_at.isoformat(),
                }
            )
            
            # Notify receiver if online
            await push_new_message(
                request.receiver_id,
                {
                    "message_id": result.message_id,
                    "sender_id": sender_id,
                    "session_id": result.session_id,
                    "content": request.content,
                    "type": request.type,
                    "created_at": result.created_at.isoformat(),
                }
            )
    
    except NotePassingException as e:
        await push_error(sender_id, e.code, e.message)
    except Exception as e:
        await push_error(sender_id, 5002, "Failed to send message")


async def handle_mark_read(device_id: str, payload: dict):
    """Handle mark_read action from WebSocket."""
    from app.database import AsyncSessionLocal
    
    try:
        # Create database session
        async with AsyncSessionLocal() as db:
            # Build request
            request = MarkReadRequest(
                device_id=device_id,
                message_ids=payload.get("message_ids", []),
            )
            
            # Mark messages as read
            result = await MessageService.mark_read(db, request)
            
            # Confirm to device
            await manager.send_personal_message(
                device_id,
                {
                    "type": "read_confirmed",
                    "payload": {
                        "updated_count": result.updated_count,
                    },
                }
            )
    
    except NotePassingException as e:
        await push_error(device_id, e.code, e.message)
    except Exception as e:
        await push_error(device_id, 5002, "Failed to mark messages as read")
