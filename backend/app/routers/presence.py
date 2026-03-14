"""
附近关系路由 - Presence相关的API端点
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    PresenceResolveRequest,
    PresenceResolveResponse,
    PresenceDisconnectRequest,
    PresenceDisconnectResponse,
    BaseResponse,
)
from app.services import PresenceService
from app.exceptions import ValidationError

router = APIRouter()


@router.post("/presence/resolve", response_model=BaseResponse[PresenceResolveResponse])
async def resolve_nearby_devices(
    request: PresenceResolveRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    解析附近设备
    
    将BLE扫描到的temp_id列表解析为用户名片
    """
    service = PresenceService(db)
    try:
        result = await service.resolve_nearby_devices(request)
        return BaseResponse(data=result)
    except ValidationError as e:
        return BaseResponse(code=e.code, message=e.message, data=None)


@router.post("/presence/disconnect", response_model=BaseResponse[PresenceDisconnectResponse])
async def report_disconnect(
    request: PresenceDisconnectRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    上报离开范围
    
    客户端检测到某设备离开蓝牙范围后通知服务器
    """
    service = PresenceService(db)
    try:
        result = await service.report_disconnect(request)
        return BaseResponse(data=result)
    except ValidationError as e:
        return BaseResponse(code=e.code, message=e.message, data=None)
