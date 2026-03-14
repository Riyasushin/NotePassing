package com.example.notepassingapp.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.example.notepassingapp.data.local.entity.MessageEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface MessageDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(entity: MessageEntity)

    /** 按时间正序，聊天页从上到下显示 */
    @Query("SELECT * FROM messages WHERE session_id = :sessionId ORDER BY created_at ASC")
    fun getBySessionId(sessionId: String): Flow<List<MessageEntity>>

    /** 取某会话最后一条消息（用于卡片预览） */
    @Query("SELECT * FROM messages WHERE session_id = :sessionId ORDER BY created_at DESC LIMIT 1")
    suspend fun getLatestBySessionId(sessionId: String): MessageEntity?

    /** 批量标记已读 */
    @Query("UPDATE messages SET status = 'read', read_at = :readAt WHERE message_id IN (:messageIds)")
    suspend fun markRead(messageIds: List<String>, readAt: Long = System.currentTimeMillis())

    /** 统计某会话中我发出的未被回复的消息数（用于非好友 2 条限制） */
    @Query("""
        SELECT COUNT(*) FROM messages 
        WHERE session_id = :sessionId AND sender_id = :myDeviceId
    """)
    suspend fun countMySentMessages(sessionId: String, myDeviceId: String): Int
}
