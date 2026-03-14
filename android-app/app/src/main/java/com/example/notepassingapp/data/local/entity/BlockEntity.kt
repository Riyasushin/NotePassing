package com.example.notepassingapp.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * block 表：屏蔽列表。
 * 被屏蔽的用户从 chatable、附近页、消息列表中全部过滤。
 */
@Entity(tableName = "blocks")
data class BlockEntity(
    @PrimaryKey
    @ColumnInfo(name = "device_id")
    val deviceId: String,

    @ColumnInfo(name = "blocked_at")
    val blockedAt: Long = System.currentTimeMillis()
)
