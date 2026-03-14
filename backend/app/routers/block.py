"""Block router."""
from fastapi import APIRouter

from app.dependencies import DbDep
from app.schemas.block import BlockRequest
from app.services.relation_service import RelationService
from app.utils.response import success_response

router = APIRouter(prefix="/block", tags=["Block"])


@router.post("", response_model=dict)
async def block_user(
    data: BlockRequest,
    db: DbDep,
) -> dict:
    """
    Block a user.
    
    - Prevents all interactions between users
    - Removes any existing friendship
    - Both users won't see each other in nearby lists
    """
    await RelationService.block_user(db, data)
    return success_response(data=None)


@router.delete("/{target_device_id}", response_model=dict)
async def unblock_user(
    target_device_id: str,
    device_id: str,
    db: DbDep,
) -> dict:
    """
    Unblock a user.
    
    - Removes the block record
    - Users can interact again
    """
    await RelationService.unblock_user(db, device_id, target_device_id)
    return success_response(data=None)
