from app.schemas.common import ResponseModel, ErrorResponse
from app.schemas.device import (
    DeviceInitRequest,
    DeviceInitResponse,
    DeviceUpdateRequest,
    DeviceProfileResponse,
)
from app.schemas.temp_id import (
    TempIDRefreshRequest,
    TempIDRefreshResponse,
)
from app.schemas.presence import (
    ScannedDevice,
    NearbyDevice,
    BoostAlert,
    PresenceResolveRequest,
    PresenceResolveResponse,
    PresenceDisconnectRequest,
    PresenceDisconnectResponse,
)
from app.schemas.message import (
    SendMessageRequest,
    SendMessageResponse,
    MessageHistoryItem,
    MessageHistoryResponse,
    MarkReadRequest,
    MarkReadResponse,
)
from app.schemas.friendship import (
    FriendItem,
    FriendListResponse,
    FriendRequestRequest,
    FriendRequestResponse,
    FriendResponseRequest,
    FriendResponseResponse,
)
from app.schemas.block import (
    BlockRequest,
)
from app.schemas.websocket import (
    WebSocketSendMessage,
    WebSocketMarkRead,
    WebSocketMessage,
    WebSocketConnected,
    WebSocketNewMessage,
    WebSocketMessageSent,
    WebSocketFriendRequest,
    WebSocketFriendResponse,
    WebSocketBoost,
    WebSocketSessionExpired,
    WebSocketMessagesRead,
    WebSocketError,
)

__all__ = [
    # Common
    "ResponseModel",
    "ErrorResponse",
    # Device
    "DeviceInitRequest",
    "DeviceInitResponse",
    "DeviceUpdateRequest",
    "DeviceProfileResponse",
    # Temp ID
    "TempIDRefreshRequest",
    "TempIDRefreshResponse",
    # Presence
    "ScannedDevice",
    "NearbyDevice",
    "BoostAlert",
    "PresenceResolveRequest",
    "PresenceResolveResponse",
    "PresenceDisconnectRequest",
    "PresenceDisconnectResponse",
    # Message
    "SendMessageRequest",
    "SendMessageResponse",
    "MessageHistoryItem",
    "MessageHistoryResponse",
    "MarkReadRequest",
    "MarkReadResponse",
    # Friendship
    "FriendItem",
    "FriendListResponse",
    "FriendRequestRequest",
    "FriendRequestResponse",
    "FriendResponseRequest",
    "FriendResponseResponse",
    # Block
    "BlockRequest",
    # WebSocket
    "WebSocketSendMessage",
    "WebSocketMarkRead",
    "WebSocketMessage",
    "WebSocketConnected",
    "WebSocketNewMessage",
    "WebSocketMessageSent",
    "WebSocketFriendRequest",
    "WebSocketFriendResponse",
    "WebSocketBoost",
    "WebSocketSessionExpired",
    "WebSocketMessagesRead",
    "WebSocketError",
]
