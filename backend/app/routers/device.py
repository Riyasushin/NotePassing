"""
设备路由 - 设备相关的API端点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    DeviceInitRequest,
    DeviceInitResponse,
    DeviceUpdateRequest,
    DeviceProfile,
    DeviceUpdateResponse,
    BaseResponse,
)
from app.services import DeviceService
from app.exceptions import (
    ValidationError,
    DeviceNotInitializedError,
)

router = APIRouter()


@router.post("/device/init", response_model=BaseResponse[DeviceInitResponse])
async def init_device(
    request: DeviceInitRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    设备初始化
    
    首次启动时调用，创建或恢复设备记录
    """
    service = DeviceService(db)
    try:
        result = await service.init_device(request)
        return BaseResponse(data=result)
    except ValidationError as e:
        return BaseResponse(code=e.code, message=e.message, data=None)


@router.get("/device/{device_id}", response_model=BaseResponse[DeviceProfile])
async def get_device_profile(
    device_id: str,
    requester_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取设备资料
    
    根据请求者与目标的关系，按隐私规则过滤字段
    """
    service = DeviceService(db)
    try:
        result = await service.get_device_profile(device_id, requester_id)
        return BaseResponse(data=result)
    except (ValidationError, DeviceNotInitializedError) as e:
        return BaseResponse(code=e.code, message=e.message, data=None)


@router.put("/device/{device_id}", response_model=BaseResponse[DeviceUpdateResponse])
async def update_device(
    device_id: str,
    request: DeviceUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    更新设备资料
    
    支持部分更新，只传需要改的字段
    """
    service = DeviceService(db)
    try:
        result = await service.update_device(device_id, request)
        return BaseResponse(data=result)
    except (ValidationError, DeviceNotInitializedError) as e:
        return BaseResponse(code=e.code, message=e.message, data=None)
