package com.example.notepassingapp.data.remote.dto

import com.google.gson.annotations.SerializedName

// ===== §5.1 获取好友列表 =====

data class FriendsListData(
    @SerializedName("friends") val friends: List<FriendItemDto>
)

data class FriendItemDto(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("nickname") val nickname: String,
    @SerializedName("avatar") val avatar: String?,
    @SerializedName("tags") val tags: List<String>,
    @SerializedName("profile") val profile: String,
    @SerializedName("is_anonymous") val isAnonymous: Boolean,
    @SerializedName("last_chat_at") val lastChatAt: String?
)

// ===== §5.2 发送好友申请 =====

data class FriendRequestBody(
    @SerializedName("sender_id") val senderId: String,
    @SerializedName("receiver_id") val receiverId: String,
    @SerializedName("message") val message: String? = null
)

data class FriendRequestData(
    @SerializedName("request_id") val requestId: String,
    @SerializedName("status") val status: String,
    @SerializedName("created_at") val createdAt: String
)

// ===== §5.3 回应好友申请 =====

data class FriendRespondBody(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("action") val action: String  // "accept" or "reject"
)

data class FriendAcceptData(
    @SerializedName("request_id") val requestId: String,
    @SerializedName("status") val status: String,
    @SerializedName("friend") val friend: FriendBriefDto?,
    @SerializedName("session_id") val sessionId: String?
)

data class FriendBriefDto(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("nickname") val nickname: String,
    @SerializedName("avatar") val avatar: String?
)

// ===== §5.5 屏蔽用户 =====

data class BlockRequest(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("target_id") val targetId: String
)
