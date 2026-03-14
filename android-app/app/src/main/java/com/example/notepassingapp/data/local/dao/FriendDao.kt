package com.example.notepassingapp.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.notepassingapp.data.local.entity.FriendEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface FriendDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOrReplace(entity: FriendEntity)

    @Update
    suspend fun update(entity: FriendEntity)

    /** 好友页按最后聊天时间排序 */
    @Query("SELECT * FROM friends ORDER BY last_chat_at DESC")
    fun getAll(): Flow<List<FriendEntity>>

    @Query("SELECT * FROM friends WHERE device_id = :deviceId")
    suspend fun getByDeviceId(deviceId: String): FriendEntity?

    @Query("SELECT * FROM friends WHERE device_id = :deviceId LIMIT 1")
    fun observeByDeviceId(deviceId: String): Flow<FriendEntity?>

    @Query("SELECT EXISTS(SELECT 1 FROM friends WHERE device_id = :deviceId)")
    suspend fun isFriend(deviceId: String): Boolean

    @Query("UPDATE friends SET is_nearby = :isNearby WHERE device_id = :deviceId")
    suspend fun updateNearbyStatus(deviceId: String, isNearby: Boolean)

    @Query("UPDATE friends SET meet_count = meet_count + 1 WHERE device_id = :deviceId")
    suspend fun incrementMeetCount(deviceId: String)

    @Query("DELETE FROM friends WHERE device_id = :deviceId")
    suspend fun delete(deviceId: String)
}
