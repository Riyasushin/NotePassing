package com.example.notepassingapp.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * messages 表：聊天消息记录。
 * type: "common"（普通消息）— heartbeat 不存库。
 * status: "sent" / "read"
 */
@Entity(tableName = "messages")
data class MessageEntity(
    @PrimaryKey
    @ColumnInfo(name = "message_id")
    val messageId: String,

    @ColumnInfo(name = "session_id")
    val sessionId: String,

    @ColumnInfo(name = "sender_id")
    val senderId: String,

    @ColumnInfo(name = "receiver_id")
    val receiverId: String,

    val content: String,
    val type: String = "common",
    val status: String = "sent",

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "read_at")
    val readAt: Long? = null
)
