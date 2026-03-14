package com.example.notepassingapp.data.remote.ws

import com.google.gson.annotations.SerializedName

// ===== 客户端发送载荷 =====

data class WsSendMessagePayload(
    @SerializedName("receiver_id") val receiverId: String,
    @SerializedName("content") val content: String,
    @SerializedName("type") val type: String = "common"
)

data class WsMarkReadPayload(
    @SerializedName("message_ids") val messageIds: List<String>
)

// ===== 服务端推送载荷 =====

data class WsConnectedPayload(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("server_time") val serverTime: String
)

data class WsNewMessagePayload(
    @SerializedName("message_id") val messageId: String,
    @SerializedName("sender_id") val senderId: String,
    @SerializedName("session_id") val sessionId: String,
    @SerializedName("content") val content: String,
    @SerializedName("type") val type: String,
    @SerializedName("created_at") val createdAt: String
)

data class WsMessageSentPayload(
    @SerializedName("message_id") val messageId: String,
    @SerializedName("session_id") val sessionId: String,
    @SerializedName("status") val status: String,
    @SerializedName("created_at") val createdAt: String
)

data class WsFriendRequestPayload(
    @SerializedName("request_id") val requestId: String,
    @SerializedName("sender") val sender: WsFriendRequestSender,
    @SerializedName("message") val message: String?
)

data class WsFriendRequestSender(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("nickname") val nickname: String,
    @SerializedName("avatar") val avatar: String?,
    @SerializedName("tags") val tags: List<String>
)

data class WsFriendResponsePayload(
    @SerializedName("request_id") val requestId: String,
    @SerializedName("status") val status: String,
    @SerializedName("friend") val friend: WsFriendBrief?,
    @SerializedName("session_id") val sessionId: String?
)

data class WsFriendBrief(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("nickname") val nickname: String
)

data class WsBoostPayload(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("nickname") val nickname: String,
    @SerializedName("distance_estimate") val distanceEstimate: Float,
    @SerializedName("timestamp") val timestamp: String
)

data class WsSessionExpiredPayload(
    @SerializedName("session_id") val sessionId: String,
    @SerializedName("peer_device_id") val peerDeviceId: String,
    @SerializedName("reason") val reason: String
)

data class WsMessagesReadPayload(
    @SerializedName("message_ids") val messageIds: List<String>,
    @SerializedName("reader_id") val readerId: String,
    @SerializedName("read_at") val readAt: String
)

data class WsErrorPayload(
    @SerializedName("code") val code: Int,
    @SerializedName("message") val message: String
)
