"""Error codes for NotePassing API."""

# Success
SUCCESS = 0

# Client errors (4xxx)
TEMP_CHAT_LIMIT_REACHED = 4001      # 临时聊天消息已达上限
TEMP_SESSION_EXPIRED = 4002         # 临时会话已过期
NOT_IN_BLUETOOTH_RANGE = 4003       # 不在蓝牙范围内
BLOCKED_BY_USER = 4004              # 已被对方屏蔽
FRIEND_REQUEST_COOLDOWN = 4005      # 好友申请冷却中
INVALID_TEMP_ID = 4006              # 无效的临时 ID
DEVICE_NOT_INITIALIZED = 4007       # 设备未初始化
FRIENDSHIP_NOT_EXIST = 4008         # 好友关系不存在
DUPLICATE_OPERATION = 4009          # 重复操作

# Parameter/Server errors (5xxx)
INVALID_PARAMS = 5001               # 参数格式错误
SERVER_ERROR = 5002                 # 服务器内部错误

# Error code to message mapping
ERROR_MESSAGES = {
    SUCCESS: "ok",
    TEMP_CHAT_LIMIT_REACHED: "临时聊天消息已达上限",
    TEMP_SESSION_EXPIRED: "临时会话已过期",
    NOT_IN_BLUETOOTH_RANGE: "不在蓝牙范围内",
    BLOCKED_BY_USER: "已被对方屏蔽",
    FRIEND_REQUEST_COOLDOWN: "好友申请冷却中",
    INVALID_TEMP_ID: "无效的临时 ID",
    DEVICE_NOT_INITIALIZED: "设备未初始化",
    FRIENDSHIP_NOT_EXIST: "好友关系不存在",
    DUPLICATE_OPERATION: "重复操作",
    INVALID_PARAMS: "参数格式错误",
    SERVER_ERROR: "服务器内部错误",
}


def get_error_message(code: int) -> str:
    """Get error message by code."""
    return ERROR_MESSAGES.get(code, "未知错误")
