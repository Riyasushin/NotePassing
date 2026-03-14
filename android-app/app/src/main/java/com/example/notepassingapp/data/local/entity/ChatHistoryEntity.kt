package com.example.notepassingapp.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * chat_history 表：记录所有曾经出现在 chatable 列表中的用户。
 * 持久化存储，不因离开蓝牙范围而删除。
 * 是附近页的数据来源。
 */
@Entity(tableName = "chat_history")
data class ChatHistoryEntity(
    @PrimaryKey
    @ColumnInfo(name = "device_id")
    val deviceId: String,

    val nickname: String = "",
    val avatar: String? = null,
    val tags: String = "[]",          // JSON 数组，用 TypeConverter 转换
    val profile: String = "",
    @ColumnInfo(name = "is_anonymous")
    val isAnonymous: Boolean = false,
    @ColumnInfo(name = "role_name")
    val roleName: String? = null,
    @ColumnInfo(name = "is_friend")
    val isFriend: Boolean = false,

    @ColumnInfo(name = "session_id")
    val sessionId: String? = null,
    @ColumnInfo(name = "last_message")
    val lastMessage: String? = null,
    @ColumnInfo(name = "last_message_at")
    val lastMessageAt: Long? = null,

    @ColumnInfo(name = "first_seen_at")
    val firstSeenAt: Long = System.currentTimeMillis(),
    @ColumnInfo(name = "last_seen_at")
    val lastSeenAt: Long = System.currentTimeMillis(),
    
    /** 
     * 会话是否已过期（非好友离开蓝牙范围超过GRACE时间）。
     * 过期后不能继续发送消息，但可查看历史记录。
     */
    @ColumnInfo(name = "is_session_expired", defaultValue = "false")
    val isSessionExpired: Boolean = false
)
