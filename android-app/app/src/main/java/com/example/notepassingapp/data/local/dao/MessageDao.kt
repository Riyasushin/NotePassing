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

    /** 按时间正序，聊天页从上到下显示（按 sessionId） */
    @Query("SELECT * FROM messages WHERE session_id = :sessionId ORDER BY created_at ASC")
    fun getBySessionId(sessionId: String): Flow<List<MessageEntity>>

    /** 按对方 deviceId 查询所有与该对象的消息（不依赖 sessionId） */
    @Query("""
        SELECT * FROM messages 
        WHERE (sender_id = :myId AND receiver_id = :peerId) 
           OR (sender_id = :peerId AND receiver_id = :myId)
        ORDER BY created_at ASC
    """)
    fun getByPeer(myId: String, peerId: String): Flow<List<MessageEntity>>

    /** 取某会话最后一条消息（用于卡片预览） */
    @Query("SELECT * FROM messages WHERE session_id = :sessionId ORDER BY created_at DESC LIMIT 1")
    suspend fun getLatestBySessionId(sessionId: String): MessageEntity?

    /** 批量标记已读 */
    @Query("UPDATE messages SET status = 'read', read_at = :readAt WHERE message_id IN (:messageIds)")
    suspend fun markRead(messageIds: List<String>, readAt: Long = System.currentTimeMillis())

    /** 统计我发给某人的消息数（用于非好友 2 条限制） */
    @Query("""
        SELECT COUNT(*) FROM messages 
        WHERE sender_id = :myDeviceId AND receiver_id = :peerId
    """)
    suspend fun countMySentToPeer(myDeviceId: String, peerId: String): Int

    /** 统计某人发给我的消息数（用于判断对方是否已回复） */
    @Query("""
        SELECT COUNT(*) FROM messages 
        WHERE sender_id = :peerId AND receiver_id = :myDeviceId
    """)
    suspend fun countPeerSentToMe(peerId: String, myDeviceId: String): Int

    @Query("""
        SELECT COUNT(*) FROM messages 
        WHERE session_id = :sessionId AND sender_id = :myDeviceId
    """)
    suspend fun countMySentMessages(sessionId: String, myDeviceId: String): Int

    @Query("DELETE FROM messages WHERE message_id = :messageId")
    suspend fun delete(messageId: String)
}
