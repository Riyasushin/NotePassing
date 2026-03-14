package com.example.notepassingapp.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.notepassingapp.data.local.entity.ChatHistoryEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ChatHistoryDao {

    /** 插入或替换（同一 device_id 再次出现时更新） */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOrReplace(entity: ChatHistoryEntity)

    @Update
    suspend fun update(entity: ChatHistoryEntity)

    /** 获取所有历史记录，UI 观察此 Flow 自动刷新 */
    @Query("SELECT * FROM chat_history ORDER BY last_seen_at DESC")
    fun getAll(): Flow<List<ChatHistoryEntity>>

    @Query("SELECT * FROM chat_history WHERE device_id = :deviceId")
    suspend fun getByDeviceId(deviceId: String): ChatHistoryEntity?

    /** 过滤掉被屏蔽的用户后的列表 */
    @Query("""
        SELECT * FROM chat_history 
        WHERE device_id NOT IN (SELECT device_id FROM blocks) 
        ORDER BY last_seen_at DESC
    """)
    fun getAllExcludeBlocked(): Flow<List<ChatHistoryEntity>>

    @Query("DELETE FROM chat_history WHERE device_id = :deviceId")
    suspend fun delete(deviceId: String)
    
    /** 标记会话已过期（非好友离开范围） */
    @Query("UPDATE chat_history SET is_session_expired = 1 WHERE device_id = :deviceId")
    suspend fun markSessionExpired(deviceId: String)
    
    /** 重置会话过期状态（重新成为好友或重新发现） */
    @Query("UPDATE chat_history SET is_session_expired = 0 WHERE device_id = :deviceId")
    suspend fun resetSessionExpired(deviceId: String)
}
