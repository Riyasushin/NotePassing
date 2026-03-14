package com.example.notepassingapp.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import com.example.notepassingapp.data.local.dao.BlockDao
import com.example.notepassingapp.data.local.dao.ChatHistoryDao
import com.example.notepassingapp.data.local.dao.FriendDao
import com.example.notepassingapp.data.local.dao.MessageDao
import com.example.notepassingapp.data.local.entity.BlockEntity
import com.example.notepassingapp.data.local.entity.ChatHistoryEntity
import com.example.notepassingapp.data.local.entity.FriendEntity
import com.example.notepassingapp.data.local.entity.MessageEntity

/**
 * Room 数据库总入口。
 * version = 1：首次创建，后续修改表结构时递增并写 Migration。
 * exportSchema = false：MVP 阶段不需要导出数据库 schema 文件。
 */
@Database(
    entities = [
        ChatHistoryEntity::class,
        FriendEntity::class,
        BlockEntity::class,
        MessageEntity::class
    ],
    version = 1,
    exportSchema = false
)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {

    abstract fun chatHistoryDao(): ChatHistoryDao
    abstract fun friendDao(): FriendDao
    abstract fun blockDao(): BlockDao
    abstract fun messageDao(): MessageDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        /**
         * 单例模式获取数据库实例。
         * synchronized 保证多线程安全，只创建一次。
         */
        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "note_passing.db"
                )
                    .fallbackToDestructiveMigration()  // MVP 阶段：表结构变了直接清库重建
                    .build()
                    .also { INSTANCE = it }
            }
        }
    }
}
