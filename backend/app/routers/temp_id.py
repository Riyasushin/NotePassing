"""
临时ID路由 - Temp ID相关的API端点
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    TempIdRefreshRequest,
    TempIdRefreshResponse,
    BaseResponse,
)
from app.services import TempIdService
from app.exceptions import ValidationError, DeviceNotInitializedError

router = APIRouter()


@router.post("/temp-id/refresh", response_model=BaseResponse[TempIdRefreshResponse])
async def refresh_temp_id(
    request: TempIdRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    刷新临时ID
    
    获取新的BLE广播ID，建议每5分钟轮换一次
    """
    service = TempIdService(db)
    try:
        result = await service.refresh_temp_id(request)
        return BaseResponse(data=result)
    except (ValidationError, DeviceNotInitializedError) as e:
        return BaseResponse(code=e.code, message=e.message, data=None)
