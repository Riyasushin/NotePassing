"""Temp ID router."""
from fastapi import APIRouter

from app.dependencies import DbDep
from app.schemas.temp_id import TempIDRefreshRequest, TempIDRefreshResponse
from app.services.temp_id_service import TempIDService
from app.utils.response import success_response

router = APIRouter(prefix="/temp-id", tags=["Temp ID"])


@router.post("/refresh", response_model=dict)
async def refresh_temp_id(
    data: TempIDRefreshRequest,
    db: DbDep,
) -> dict:
    """
    Generate a new temporary ID for BLE broadcast.
    
    - Clients should call this endpoint:
      1. On app startup to get the first temp_id
      2. Before the current temp_id expires (expires_at)
    
    - If current_temp_id is provided, it will be marked for expiration
      in 5 minutes (buffer period), allowing for smooth transition
    
    - The new temp_id is valid for 10 minutes (5 min active + 5 min buffer)
    """
    result = await TempIDService.refresh_temp_id(db, data)
    return success_response(data=result.model_dump())
