"""
WebSocket管理器 - 管理WebSocket连接和消息推送
"""

import json
from typing import Dict, Optional, Set
from fastapi import WebSocket


class WebSocketManager:
    """
    WebSocket连接管理器
    
    管理所有WebSocket连接，负责消息推送
    V2变更：不维护在线状态，只管理连接
    """
    
    def __init__(self):
        # 设备ID到WebSocket连接的映射
        self.connections: Dict[str, WebSocket] = {}
    
    async def connect(self, device_id: str, websocket: WebSocket) -> None:
        """
        建立WebSocket连接
        
        Args:
            device_id: 设备ID
            websocket: WebSocket连接对象
        """
        await websocket.accept()
        self.connections[device_id] = websocket
        
        # 发送连接确认
        await self.send_message(device_id, {
            "type": "connected",
            "payload": {
                "device_id": device_id,
                "server_time": self._get_iso_timestamp()
            }
        })
    
    def disconnect(self, device_id: str) -> None:
        """
        断开WebSocket连接
        
        Args:
            device_id: 设备ID
        """
        if device_id in self.connections:
            del self.connections[device_id]
    
    async def send_message(
        self,
        device_id: str,
        message: dict
    ) -> bool:
        """
        向指定设备发送消息
        
        V2变更：不判断在线状态，直接尝试发送
        
        Args:
            device_id: 目标设备ID
            message: 消息内容
            
        Returns:
            是否发送成功
        """
        websocket = self.connections.get(device_id)
        if not websocket:
            return False
        
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            # 发送失败，移除连接
            self.disconnect(device_id)
            return False
    
    async def broadcast(
        self,
        device_ids: list,
        message: dict
    ) -> Dict[str, bool]:
        """
        向多个设备广播消息
        
        Args:
            device_ids: 目标设备ID列表
            message: 消息内容
            
        Returns:
            每个设备的发送结果
        """
        results = {}
        for device_id in device_ids:
            success = await self.send_message(device_id, message)
            results[device_id] = success
        return results
    
    def is_connected(self, device_id: str) -> bool:
        """
        检查设备是否已连接
        
        注意：仅用于检查WebSocket连接状态，不是业务在线状态
        """
        return device_id in self.connections
    
    def get_connected_devices(self) -> Set[str]:
        """获取所有已连接的设备ID"""
        return set(self.connections.keys())
    
    def _get_iso_timestamp(self) -> str:
        """获取ISO格式时间戳"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
    
    # ========== 便捷方法：各种消息类型的推送 ==========
    
    async def send_new_message(
        self,
        device_id: str,
        message_id: str,
        sender_id: str,
        session_id: str,
        content: str,
        msg_type: str,
        created_at: str
    ) -> bool:
        """推送新消息通知"""
        return await self.send_message(device_id, {
            "type": "new_message",
            "payload": {
                "message_id": message_id,
                "sender_id": sender_id,
                "session_id": session_id,
                "content": content,
                "type": msg_type,
                "created_at": created_at,
            }
        })
    
    async def send_message_sent(
        self,
        device_id: str,
        message_id: str,
        session_id: str,
        created_at: str
    ) -> bool:
        """推送消息发送确认"""
        return await self.send_message(device_id, {
            "type": "message_sent",
            "payload": {
                "message_id": message_id,
                "session_id": session_id,
                "status": "sent",
                "created_at": created_at,
            }
        })
    
    async def send_friend_request(
        self,
        device_id: str,
        request_id: str,
        sender: dict,
        message: str
    ) -> bool:
        """推送好友申请通知"""
        return await self.send_message(device_id, {
            "type": "friend_request",
            "payload": {
                "request_id": request_id,
                "sender": sender,
                "message": message,
            }
        })
    
    async def send_friend_response(
        self,
        device_id: str,
        request_id: str,
        status: str,
        friend: dict = None,
        session_id: str = None
    ) -> bool:
        """推送好友申请结果通知"""
        payload = {
            "request_id": request_id,
            "status": status,
        }
        if friend:
            payload["friend"] = friend
        if session_id:
            payload["session_id"] = session_id
        
        return await self.send_message(device_id, {
            "type": "friend_response",
            "payload": payload
        })
    
    async def send_boost(
        self,
        device_id: str,
        friend_id: str,
        nickname: str,
        distance: float
    ) -> bool:
        """推送Boost通知"""
        return await self.send_message(device_id, {
            "type": "boost",
            "payload": {
                "device_id": friend_id,
                "nickname": nickname,
                "distance_estimate": distance,
                "timestamp": self._get_iso_timestamp(),
            }
        })
    
    async def send_session_expired(
        self,
        device_id: str,
        session_id: str,
        peer_id: str,
        reason: str = "out_of_range"
    ) -> bool:
        """推送会话过期通知"""
        return await self.send_message(device_id, {
            "type": "session_expired",
            "payload": {
                "session_id": session_id,
                "peer_device_id": peer_id,
                "reason": reason,
            }
        })
    
    async def send_messages_read(
        self,
        device_id: str,
        message_ids: list,
        reader_id: str
    ) -> bool:
        """推送消息已读通知"""
        return await self.send_message(device_id, {
            "type": "messages_read",
            "payload": {
                "message_ids": message_ids,
                "reader_id": reader_id,
                "read_at": self._get_iso_timestamp(),
            }
        })
    
    async def send_error(
        self,
        device_id: str,
        code: int,
        message: str
    ) -> bool:
        """推送错误通知"""
        return await self.send_message(device_id, {
            "type": "error",
            "payload": {
                "code": code,
                "message": message,
            }
        })
    
    async def send_pong(self, device_id: str) -> bool:
        """发送心跳响应"""
        return await self.send_message(device_id, {"type": "pong"})


# 全局WebSocket管理器实例
ws_manager = WebSocketManager()
