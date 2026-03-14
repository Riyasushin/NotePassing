package com.example.notepassingapp.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.example.notepassingapp.data.local.dao.BlockDao
import com.example.notepassingapp.data.local.dao.ChatHistoryDao
import com.example.notepassingapp.data.local.dao.FriendDao
import com.example.notepassingapp.data.local.dao.FriendRequestDao
import com.example.notepassingapp.data.local.dao.MessageDao
import com.example.notepassingapp.data.local.entity.BlockEntity
import com.example.notepassingapp.data.local.entity.ChatHistoryEntity
import com.example.notepassingapp.data.local.entity.FriendEntity
import com.example.notepassingapp.data.local.entity.FriendRequestEntity
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
        FriendRequestEntity::class,
        BlockEntity::class,
        MessageEntity::class
    ],
    version = 2,
    exportSchema = false
)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {

    abstract fun chatHistoryDao(): ChatHistoryDao
    abstract fun friendDao(): FriendDao
    abstract fun friendRequestDao(): FriendRequestDao
    abstract fun blockDao(): BlockDao
    abstract fun messageDao(): MessageDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        private val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    """
                    CREATE TABLE IF NOT EXISTS `friend_requests` (
                        `request_id` TEXT NOT NULL,
                        `peer_device_id` TEXT NOT NULL,
                        `peer_nickname` TEXT NOT NULL,
                        `peer_avatar` TEXT,
                        `message` TEXT,
                        `direction` TEXT NOT NULL,
                        `created_at` INTEGER NOT NULL,
                        PRIMARY KEY(`request_id`)
                    )
                    """.trimIndent()
                )
            }
        }

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
                    .addMigrations(MIGRATION_1_2)
                    .fallbackToDestructiveMigration()  // MVP 阶段：表结构变了直接清库重建
                    .build()
                    .also { INSTANCE = it }
            }
        }
    }
}
