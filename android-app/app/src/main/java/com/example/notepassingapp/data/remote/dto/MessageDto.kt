package com.example.notepassingapp.data.remote.dto

import com.google.gson.annotations.SerializedName

// ===== §4.1 发送消息 =====

data class SendMessageRequest(
    @SerializedName("sender_id") val senderId: String,
    @SerializedName("receiver_id") val receiverId: String,
    @SerializedName("content") val content: String,
    @SerializedName("type") val type: String = "common"
)

data class SendMessageData(
    @SerializedName("message_id") val messageId: String,
    @SerializedName("session_id") val sessionId: String,
    @SerializedName("status") val status: String,
    @SerializedName("created_at") val createdAt: String
)

// ===== §4.2 获取历史消息 =====

data class MessageHistoryData(
    @SerializedName("session_id") val sessionId: String,
    @SerializedName("messages") val messages: List<MessageItemDto>,
    @SerializedName("has_more") val hasMore: Boolean
)

data class MessageItemDto(
    @SerializedName("message_id") val messageId: String,
    @SerializedName("sender_id") val senderId: String,
    @SerializedName("content") val content: String,
    @SerializedName("type") val type: String,
    @SerializedName("status") val status: String,
    @SerializedName("created_at") val createdAt: String
)

// ===== §4.3 标记已读 =====

data class MarkReadRequest(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("message_ids") val messageIds: List<String>
)

data class MarkReadData(
    @SerializedName("updated_count") val updatedCount: Int
)
