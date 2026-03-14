"""Presence router for BLE nearby device resolution."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.presence import (
    PresenceResolveRequest,
    PresenceResolveResponse,
    PresenceDisconnectRequest,
    PresenceDisconnectResponse,
)
from app.services.presence_service import PresenceService


router = APIRouter(prefix="/presence", tags=["presence"])


@router.post("/resolve", response_model=dict)
async def resolve_presence(
    data: PresenceResolveRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Resolve scanned temp IDs to device profiles.
    
    Uploads a list of BLE-scanned temp IDs and RSSI values,
    returns resolved device profiles with distance estimates.
    May include boost alerts for friends coming nearby.
    """
    result = await PresenceService.resolve_nearby_devices(db, data)
    return {
        "code": 0,
        "message": "Nearby devices resolved successfully",
        "data": result.model_dump(),
    }


@router.post("/disconnect", response_model=dict)
async def report_disconnect(
    data: PresenceDisconnectRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Report a device leaving Bluetooth range.
    
    Expires any active temporary session between the two devices.
    """
    result = await PresenceService.report_disconnect(db, data)
    return {
        "code": 0,
        "message": "Disconnect reported successfully",
        "data": result.model_dump(),
    }
