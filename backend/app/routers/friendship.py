"""Friendship router."""
from fastapi import APIRouter

from app.dependencies import DbDep
from app.schemas.friendship import (
    FriendListResponse,
    FriendRequestRequest,
    FriendRequestResponse,
    FriendResponseRequest,
    FriendResponseResponse,
)
from app.services.relation_service import RelationService
from app.utils.response import success_response

router = APIRouter(prefix="/friends", tags=["Friendship"])


@router.get("", response_model=dict)
async def get_friends(
    device_id: str,
    db: DbDep,
) -> dict:
    """
    Get friend list.
    
    - Returns all accepted friendships for the device
    - Includes friend profile information
    """
    result = await RelationService.get_friends(db, device_id)
    return success_response(data=result.model_dump())


@router.post("/request", response_model=dict)
async def send_friend_request(
    data: FriendRequestRequest,
    db: DbDep,
) -> dict:
    """
    Send a friend request.
    
    - Creates a pending friendship record
    - Checks for blocks (4004 if blocked)
    - Checks for 24h cooldown after rejection (4005)
    - Checks for duplicate requests (4009)
    """
    result = await RelationService.send_friend_request(db, data)
    return success_response(data=result.model_dump())


@router.put("/{request_id}", response_model=dict)
async def respond_friend_request(
    request_id: str,
    data: FriendResponseRequest,
    db: DbDep,
) -> dict:
    """
    Respond to a friend request.
    
    - action: "accept" or "reject"
    - Accept: Creates permanent session, returns friend info
    - Reject: Sets 24h cooldown before re-request
    """
    result = await RelationService.respond_friend_request(db, request_id, data)
    return success_response(data=result.model_dump())


@router.delete("/{friend_device_id}", response_model=dict)
async def delete_friend(
    friend_device_id: str,
    device_id: str,
    db: DbDep,
) -> dict:
    """
    Delete a friendship.
    
    - Removes the friendship record
    - Session may be downgraded to temporary
    """
    await RelationService.delete_friend(db, device_id, friend_device_id)
    return success_response(data=None)
