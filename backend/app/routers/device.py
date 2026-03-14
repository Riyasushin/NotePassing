"""Device router."""
from fastapi import APIRouter, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbDep
from app.schemas.device import (
    DeviceInitRequest,
    DeviceInitResponse,
    DeviceUpdateRequest,
    DeviceProfileResponse,
)
from app.services.device_service import DeviceService
from app.utils.response import success_response

router = APIRouter(prefix="/device", tags=["Device"])


@router.post("/init", response_model=dict, status_code=status.HTTP_200_OK)
async def init_device(
    data: DeviceInitRequest,
    db: DbDep,
) -> dict:
    """
    Initialize or recover a device.
    
    - If device_id exists: returns is_new=false (recovery)
    - If device_id is new: creates device and returns is_new=true
    """
    result = await DeviceService.init_device(db, data)
    
    # Determine status code based on is_new
    status_code = status.HTTP_201_CREATED if result.is_new else status.HTTP_200_OK
    
    return success_response(
        data=result.model_dump(),
        message="ok",
    )


@router.get("/{device_id}", response_model=dict)
async def get_device(
    device_id: str,
    requester_id: str,
    db: DbDep,
) -> dict:
    """
    Get device profile with privacy filtering.
    
    - requester_id: The device ID making the request (for privacy check)
    - Privacy rules are applied based on friendship status and anonymous mode
    """
    result = await DeviceService.get_device(db, device_id, requester_id)
    return success_response(data=result.model_dump())


@router.put("/{device_id}", response_model=dict)
async def update_device(
    device_id: str,
    data: DeviceUpdateRequest,
    db: DbDep,
) -> dict:
    """
    Update device profile (partial update).
    
    Only provided fields will be updated. Fields not provided remain unchanged.
    """
    result = await DeviceService.update_device(db, device_id, data)
    return success_response(data=result)
