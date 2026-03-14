"""
路由模块 - 导出所有路由器
"""

from app.routers.device import router as device_router
from app.routers.temp_id import router as temp_id_router
from app.routers.presence import router as presence_router
from app.routers.message import router as message_router
from app.routers.friendship import router as friendship_router
from app.routers.websocket import router as websocket_router

__all__ = [
    "device_router",
    "temp_id_router",
    "presence_router",
    "message_router",
    "friendship_router",
    "websocket_router",
]
