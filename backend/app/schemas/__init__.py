"""
Schema模块 - 导出所有Pydantic模型
"""

from app.schemas.common import (
    BaseResponse,
    ErrorResponse,
    PaginationParams,
    PaginatedResponse,
)
from app.schemas.device import (
    DeviceInitRequest,
    DeviceInitResponse,
    DeviceUpdateRequest,
    DeviceProfile,
    DeviceUpdateResponse,
)
from app.schemas.temp_id import (
    TempIdRefreshRequest,
    TempIdRefreshResponse,
)
from app.schemas.presence import (
    PresenceResolveRequest,
    PresenceResolveResponse,
    NearbyDevice,
    BoostAlert,
    PresenceDisconnectRequest,
    PresenceDisconnectResponse,
)
from app.schemas.message import (
    SendMessageRequest,
    SendMessageResponse,
    MessageItem,
    GetMessagesResponse,
    MarkReadRequest,
    MarkReadResponse,
)
from app.schemas.friendship import (
    FriendItem,
    GetFriendsResponse,
    SendFriendRequest,
    SendFriendRequestResponse,
    RespondFriendRequest,
    AcceptFriendResponse,
    RejectFriendResponse,
    BlockUserRequest,
)

__all__ = [
    # Common
    "BaseResponse",
    "ErrorResponse",
    "PaginationParams",
    "PaginatedResponse",
    # Device
    "DeviceInitRequest",
    "DeviceInitResponse",
    "DeviceUpdateRequest",
    "DeviceProfile",
    "DeviceUpdateResponse",
    # Temp ID
    "TempIdRefreshRequest",
    "TempIdRefreshResponse",
    # Presence
    "PresenceResolveRequest",
    "PresenceResolveResponse",
    "NearbyDevice",
    "BoostAlert",
    "PresenceDisconnectRequest",
    "PresenceDisconnectResponse",
    # Message
    "SendMessageRequest",
    "SendMessageResponse",
    "MessageItem",
    "GetMessagesResponse",
    "MarkReadRequest",
    "MarkReadResponse",
    # Friendship
    "FriendItem",
    "GetFriendsResponse",
    "SendFriendRequest",
    "SendFriendRequestResponse",
    "RespondFriendRequest",
    "AcceptFriendResponse",
    "RejectFriendResponse",
    "BlockUserRequest",
]
