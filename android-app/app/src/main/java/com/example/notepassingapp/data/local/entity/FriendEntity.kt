package com.example.notepassingapp.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * friend 表：好友列表。
 * meet_count 和 is_nearby 是本地独有字段，不与服务器同步。
 */
@Entity(tableName = "friends")
data class FriendEntity(
    @PrimaryKey
    @ColumnInfo(name = "device_id")
    val deviceId: String,

    val nickname: String = "",
    val avatar: String? = null,
    val tags: String = "[]",
    val profile: String = "",
    @ColumnInfo(name = "is_anonymous")
    val isAnonymous: Boolean = false,

    @ColumnInfo(name = "session_id")
    val sessionId: String? = null,

    // 本地独有：见面次数，Boost 触发时 +1
    @ColumnInfo(name = "meet_count")
    val meetCount: Int = 0,

    // 本地独有：当前是否在蓝牙范围内（好友页 Boost 高亮）
    @ColumnInfo(name = "is_nearby")
    val isNearby: Boolean = false,

    @ColumnInfo(name = "last_chat_at")
    val lastChatAt: Long? = null,

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis()
)
