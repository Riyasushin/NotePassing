package com.example.notepassingapp.data.model

/**
 * 附近页卡片的 UI 数据模型。
 * 合并了 Room 持久化数据 (chat_history) 和内存实时状态 (chatable)。
 */
data class NearbyUser(
    val deviceId: String,
    val nickname: String,
    val avatar: String? = null,
    val profile: String = "",
    val isAnonymous: Boolean = false,
    val roleName: String? = null,
    val isFriend: Boolean = false,

    val state: NearbyState = NearbyState.ACTIVE,
    val rssi: Int = -100,             // 信号强度，越大越近（如 -50 比 -80 近）
    val distanceEstimate: Float = 0f, // 估算距离（米）
    val leftAt: Long? = null,         // 离开时间戳（grace 态用）
    val friendRequestState: FriendRequestState = FriendRequestState.NONE,

    val sessionId: String? = null,
    val lastMessage: String? = null,
    val lastMessageAt: Long? = null
)

enum class NearbyState {
    ACTIVE,   // 在蓝牙范围内或收到心跳
    GRACE,    // 离开范围 ≤1 分钟，仍可聊天
    EXPIRED   // 离开 >1 分钟，非好友临时会话过期
}

enum class FriendRequestState {
    NONE,
    OUTGOING_PENDING,
    INCOMING_PENDING
}
