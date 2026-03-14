"""
WebSocket路由 - WebSocket连接处理
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session_maker
from app.services import ws_manager, MessagingService, RelationService
from app.schemas import SendMessageRequest, MarkReadRequest
from app.exceptions import NotePassingException

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    device_id: str = Query(...)
):
    """
    WebSocket连接端点
    
    URL参数: device_id - 设备ID
    
    客户端消息格式:
    {
        "action": "send_message" | "mark_read" | "ping",
        "payload": {...}
    }
    """
    # 建立连接
    await ws_manager.connect(device_id, websocket)
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            
            # 处理消息
            await handle_client_message(device_id, data)
            
    except WebSocketDisconnect:
        ws_manager.disconnect(device_id)
    except Exception as e:
        # 发送错误信息
        await ws_manager.send_error(device_id, 5002, str(e))
        ws_manager.disconnect(device_id)


async def handle_client_message(device_id: str, data: dict):
    """
    处理客户端发来的WebSocket消息
    """
    action = data.get("action")
    payload = data.get("payload", {})
    
    if action == "send_message":
        await handle_send_message(device_id, payload)
    elif action == "mark_read":
        await handle_mark_read(device_id, payload)
    elif action == "ping":
        await ws_manager.send_pong(device_id)
    else:
        await ws_manager.send_error(device_id, 5001, f"未知action: {action}")


async def handle_send_message(sender_id: str, payload: dict):
    """处理发送消息请求"""
    async with async_session_maker() as db:
        try:
            # 构建请求
            request = SendMessageRequest(
                sender_id=sender_id,
                receiver_id=payload.get("receiver_id"),
                content=payload.get("content"),
                type=payload.get("type", "common")
            )
            
            # 调用服务
            service = MessagingService(db)
            result = await service.send_message(request)
            
            # 推送给接收者
            await ws_manager.send_new_message(
                device_id=request.receiver_id,
                message_id=result["message_id"],
                sender_id=sender_id,
                session_id=result["session_id"],
                content=request.content,
                msg_type=request.type,
                created_at=result["created_at"]
            )
            
            # 确认给发送者
            await ws_manager.send_message_sent(
                device_id=sender_id,
                message_id=result["message_id"],
                session_id=result["session_id"],
                created_at=result["created_at"]
            )
            
        except NotePassingException as e:
            await ws_manager.send_error(sender_id, e.code, e.message)
        except Exception as e:
            await ws_manager.send_error(sender_id, 5002, str(e))


async def handle_mark_read(reader_id: str, payload: dict):
    """处理标记已读请求"""
    async with async_session_maker() as db:
        try:
            # 构建请求
            request = MarkReadRequest(
                device_id=reader_id,
                message_ids=payload.get("message_ids", [])
            )
            
            # 调用服务
            service = MessagingService(db)
            result = await service.mark_messages_read(request)
            
            # 通知发送者
            for sender_id in result.get("sender_ids", []):
                await ws_manager.send_messages_read(
                    device_id=sender_id,
                    message_ids=request.message_ids,
                    reader_id=reader_id
                )
            
        except NotePassingException as e:
            await ws_manager.send_error(reader_id, e.code, e.message)
        except Exception as e:
            await ws_manager.send_error(reader_id, 5002, str(e))
