package com.example.notepassingapp.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.example.notepassingapp.data.local.entity.BlockEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface BlockDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(entity: BlockEntity)

    @Query("SELECT * FROM blocks")
    fun getAll(): Flow<List<BlockEntity>>

    /** 快速判断某用户是否被屏蔽 */
    @Query("SELECT EXISTS(SELECT 1 FROM blocks WHERE device_id = :deviceId)")
    suspend fun isBlocked(deviceId: String): Boolean

    @Query("DELETE FROM blocks WHERE device_id = :deviceId")
    suspend fun delete(deviceId: String)
}
