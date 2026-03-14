"""Presence router for BLE nearby device resolution."""
from fastapi import APIRouter

from app.dependencies import DbDep
from app.schemas.presence import (
    PresenceResolveRequest,
    PresenceDisconnectRequest,
)
from app.services.presence_service import PresenceService
from app.utils.response import success_response

router = APIRouter(prefix="/presence", tags=["presence"])


@router.post("/resolve", response_model=dict)
async def resolve_presence(
    data: PresenceResolveRequest,
    db: DbDep,
) -> dict:
    """Resolve scanned temp IDs to device profiles."""
    result = await PresenceService.resolve_nearby_devices(db, data)
    return success_response(data=result.model_dump())


@router.post("/disconnect", response_model=dict)
async def report_disconnect(
    data: PresenceDisconnectRequest,
    db: DbDep,
) -> dict:
    """Report a device leaving Bluetooth range."""
    result = await PresenceService.report_disconnect(db, data)
    return success_response(data=result.model_dump())
