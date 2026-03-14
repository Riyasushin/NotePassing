"""
好友关系路由 - Friendship相关的API端点
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    GetFriendsResponse,
    SendFriendRequest,
    SendFriendRequestResponse,
    RespondFriendRequest,
    AcceptFriendResponse,
    RejectFriendResponse,
    BlockUserRequest,
    BaseResponse,
    FriendItem,
)
from app.services import RelationService, ws_manager
from app.exceptions import (
    ValidationError,
    DeviceNotInitializedError,
    FriendshipNotFoundError,
    DuplicateOperationError,
    BlockedError,
    CooldownError,
)

router = APIRouter()


@router.get("/friends", response_model=BaseResponse[GetFriendsResponse])
async def get_friends_list(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取好友列表
    
    返回用户所有好友，按最后聊天时间排序
    """
    service = RelationService(db)
    try:
        friends = await service.get_friends_list(device_id)
        return BaseResponse(data={"friends": friends})
    except ValidationError as e:
        return BaseResponse(code=e.code, message=e.message, data=None)


@router.post("/friends/request", response_model=BaseResponse[SendFriendRequestResponse])
async def send_friend_request(
    request: SendFriendRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    发送好友申请
    
    向指定用户发送好友申请
    """
    service = RelationService(db)
    try:
        result = await service.send_friend_request(request)
        
        # WebSocket推送
        sender = await service._get_device_info(request.sender_id)
        await ws_manager.send_friend_request(
            device_id=request.receiver_id,
            request_id=result["request_id"],
            sender=sender,
            message=request.message or ""
        )
        
        return BaseResponse(data=result)
    except (
        ValidationError,
        BlockedError,
        CooldownError,
        DuplicateOperationError
    ) as e:
        return BaseResponse(code=e.code, message=e.message, data=None)


@router.put("/friends/{request_id}")
async def respond_friend_request(
    request_id: str,
    request: RespondFriendRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    回应好友申请
    
    action: accept 或 reject
    """
    service = RelationService(db)
    try:
        result = await service.respond_friend_request(request_id, request)
        
        # WebSocket通知申请方
        if result["status"] == "accepted":
            friend = result.get("friend", {})
            await ws_manager.send_friend_response(
                device_id=friend.get("device_id", ""),
                request_id=result["request_id"],
                status="accepted",
                friend={
                    "device_id": request.device_id,
                    "nickname": friend.get("nickname", "")
                },
                session_id=result.get("session_id")
            )
        else:
            # 获取申请方ID
            # TODO: 从数据库查询sender_id
            pass
        
        return BaseResponse(data=result)
    except (
        ValidationError,
        FriendshipNotFoundError
    ) as e:
        return BaseResponse(code=e.code, message=e.message, data=None)


@router.delete("/friends/{friend_device_id}")
async def delete_friend(
    friend_device_id: str,
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    删除好友
    """
    service = RelationService(db)
    try:
        await service.delete_friend(device_id, friend_device_id)
        return BaseResponse(data=None)
    except ValidationError as e:
        return BaseResponse(code=e.code, message=e.message, data=None)


@router.post("/block")
async def block_user(
    request: BlockUserRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    屏蔽用户
    
    屏蔽后双方互不可见
    """
    service = RelationService(db)
    try:
        await service.block_user(request)
        return BaseResponse(data=None)
    except ValidationError as e:
        return BaseResponse(code=e.code, message=e.message, data=None)


@router.delete("/block/{target_device_id}")
async def unblock_user(
    target_device_id: str,
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    取消屏蔽用户
    """
    service = RelationService(db)
    try:
        await service.unblock_user(device_id, target_device_id)
        return BaseResponse(data=None)
    except ValidationError as e:
        return BaseResponse(code=e.code, message=e.message, data=None)
