"""Device router."""
from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas.device import (
    DeviceInitRequest,
    DeviceUpdateRequest,
)
from app.services.device_service import DeviceService
from app.utils.response import success_response

router = APIRouter(prefix="/device", tags=["Device"])
settings = get_settings()


def _resolve_public_base_url(request: Request) -> str:
    configured_base = (settings.public_base_url or "").strip().rstrip("/")
    if configured_base:
        return configured_base

    forwarded_proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "http")
    forwarded_proto = forwarded_proto.split(",", 1)[0].strip()

    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if forwarded_host:
        host = forwarded_host.split(",", 1)[0].strip()
        return f"{forwarded_proto}://{host}"

    return str(request.base_url).rstrip("/")


@router.post("/init", response_model=dict)
async def init_device(
    data: DeviceInitRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Initialize or recover a device.
    
    - If device_id exists: returns is_new=false (recovery)
    - If device_id is new: creates device and returns is_new=true
    """
    result = await DeviceService.init_device(db, data)
    return success_response(data=result.model_dump())


@router.get("/{device_id}", response_model=dict)
async def get_device(
    device_id: str,
    requester_id: str,
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Update device profile (partial update).
    
    Only provided fields will be updated. Fields not provided remain unchanged.
    """
    result = await DeviceService.update_device(db, device_id, data)
    return success_response(data=result)


@router.post("/{device_id}/avatar", response_model=dict)
async def upload_avatar(
    device_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
) -> dict:
    """Upload a local avatar image and write the resulting URL back to the device profile."""
    try:
        content = await file.read()
    finally:
        await file.close()

    result = await DeviceService.upload_avatar(
        db=db,
        device_id=device_id,
        filename=file.filename,
        content_type=file.content_type,
        content=content,
        public_base_url=_resolve_public_base_url(request),
    )
    return success_response(data=result.model_dump())
