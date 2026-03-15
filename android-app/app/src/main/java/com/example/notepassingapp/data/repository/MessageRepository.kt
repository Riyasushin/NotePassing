package com.example.notepassingapp.data.repository

import android.util.Log
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.local.entity.ChatHistoryEntity
import com.example.notepassingapp.data.local.entity.MessageEntity
import com.example.notepassingapp.data.remote.ApiClient
import com.example.notepassingapp.data.remote.dto.SendMessageRequest
import com.example.notepassingapp.util.DeviceManager
import java.util.UUID
import java.time.Instant
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

/**
 * 消息仓库：WebSocket 优先发送，失败时降级到 HTTP。
 * 同时维护本地 Room 数据库。
 */
object MessageRepository {

    private const val TAG = "MessageRepository"
    private val messageDao = NotePassingApp.instance.database.messageDao()
    private val chatHistoryDao = NotePassingApp.instance.database.chatHistoryDao()
    private val friendDao = NotePassingApp.instance.database.friendDao()

    /**
     * 发送消息：先存本地 → WS 优先 / HTTP 降级。
     * 使用 HTTP 确保能拿到服务器返回的 session_id 和 message_id。
     */
    suspend fun sendMessage(
        peerDeviceId: String,
        content: String,
        type: String = "common"
    ): Boolean {
        val myDeviceId = DeviceManager.getDeviceId()
        val localMsgId = UUID.randomUUID().toString()

        val entity = MessageEntity(
            messageId = localMsgId,
            sessionId = "pending",
            senderId = myDeviceId,
            receiverId = peerDeviceId,
            content = content,
            type = type,
            status = "sending"
        )
        messageDao.insert(entity)
        updateChatHistoryPreview(peerDeviceId, content)

        return try {
            val request = SendMessageRequest(
                senderId = myDeviceId,
                receiverId = peerDeviceId,
                content = content,
                type = type
            )
            val response = ApiClient.messageApi.sendMessage(request)
            if (response.isSuccess) {
                val data = response.data!!
                val createdAtMillis = parseIsoToMillis(data.createdAt)
                messageDao.delete(localMsgId)
                messageDao.insert(entity.copy(
                    messageId = data.messageId,
                    sessionId = data.sessionId,
                    status = data.status,
                    createdAt = createdAtMillis
                ))
                upsertConversationState(
                    peerDeviceId = peerDeviceId,
                    sessionId = data.sessionId,
                    content = content,
                    messageAtMillis = createdAtMillis,
                )
                Log.d(TAG, "Sent via HTTP: msgId=${data.messageId}")
                true
            } else {
                Log.w(TAG, "HTTP send failed: ${response.code} ${response.message}")
                false
            }
        } catch (e: Exception) {
            Log.e(TAG, "HTTP send error", e)
            false
        }
    }

    /**
     * 全局消息同步：拉取本设备所有在 [after] 之后收到的消息。
     * 用于 WS 重连后的全局补漏。
     */
    suspend fun syncAllMessages(): Int {
        val myDeviceId = DeviceManager.getDeviceId()
        val latestTs = messageDao.getLatestReceivedTimestamp(myDeviceId) ?: 0L
        val afterIso = if (latestTs > 0) Instant.ofEpochMilli(latestTs).toString() else "2000-01-01T00:00:00Z"

        return try {
            val response = ApiClient.messageApi.syncMessages(
                deviceId = myDeviceId,
                after = afterIso
            )
            if (response.isSuccess && response.data != null) {
                val items = response.data.messages
                if (items.isEmpty()) {
                    Log.d(TAG, "Sync: no missed messages")
                    return 0
                }
                val entities = items.map { dto ->
                    MessageEntity(
                        messageId = dto.messageId,
                        sessionId = dto.sessionId,
                        senderId = dto.senderId,
                        receiverId = dto.receiverId,
                        content = dto.content,
                        type = dto.type,
                        status = "received",
                        createdAt = parseIsoToMillis(dto.createdAt)
                    )
                }
                messageDao.insertIgnoreAll(entities)
                items.groupBy { it.senderId }.forEach { (senderId, msgs) ->
                    val latest = msgs.maxByOrNull { parseIsoToMillis(it.createdAt) }
                    if (latest != null) {
                        upsertConversationState(
                            peerDeviceId = senderId,
                            sessionId = latest.sessionId,
                            content = latest.content,
                            messageAtMillis = parseIsoToMillis(latest.createdAt),
                        )
                    }
                }
                Log.d(TAG, "Sync: pulled ${items.size} missed messages")
                items.size
            } else {
                Log.w(TAG, "Sync failed: ${response.code} ${response.message}")
                0
            }
        } catch (e: Exception) {
            Log.e(TAG, "Sync error", e)
            0
        }
    }

    /**
     * 单会话同步：拉取某个 session 在本地最新消息之后的增量。
     * 用于进入聊天页时补漏。
     */
    suspend fun syncSessionMessages(sessionId: String, peerDeviceId: String): Int {
        if (sessionId.isBlank() || sessionId == "pending") return 0

        val myDeviceId = DeviceManager.getDeviceId()
        val latestTs = messageDao.getLatestTimestampForSession(sessionId) ?: 0L
        val afterIso = if (latestTs > 0) Instant.ofEpochMilli(latestTs).toString() else "2000-01-01T00:00:00Z"

        return try {
            val response = ApiClient.messageApi.getHistory(
                sessionId = sessionId,
                deviceId = myDeviceId,
                after = afterIso,
                limit = 50
            )
            if (response.isSuccess && response.data != null) {
                val items = response.data.messages
                if (items.isEmpty()) return 0
                val entities = items.map { dto ->
                    MessageEntity(
                        messageId = dto.messageId,
                        sessionId = sessionId,
                        senderId = dto.senderId,
                        receiverId = if (dto.senderId == myDeviceId) peerDeviceId else myDeviceId,
                        content = dto.content,
                        type = dto.type,
                        status = if (dto.senderId == myDeviceId) dto.status else "received",
                        createdAt = parseIsoToMillis(dto.createdAt)
                    )
                }
                messageDao.insertIgnoreAll(entities)
                val latest = entities.maxByOrNull { it.createdAt }
                if (latest != null) {
                    upsertConversationState(
                        peerDeviceId = peerDeviceId,
                        sessionId = sessionId,
                        content = latest.content,
                        messageAtMillis = latest.createdAt,
                    )
                }
                Log.d(TAG, "Session sync: pulled ${items.size} messages for $sessionId")
                items.size
            } else {
                Log.w(TAG, "Session sync failed: ${response.code} ${response.message}")
                0
            }
        } catch (e: Exception) {
            Log.e(TAG, "Session sync error", e)
            0
        }
    }

    fun parseServerTimestamp(iso: String): Long = parseIsoToMillis(iso)

    suspend fun upsertConversationState(
        peerDeviceId: String,
        sessionId: String,
        content: String,
        messageAtMillis: Long,
    ) {
        val history = chatHistoryDao.getByDeviceId(peerDeviceId)
        val friend = friendDao.getByDeviceId(peerDeviceId)

        if (history != null) {
            chatHistoryDao.insertOrReplace(
                history.copy(
                    sessionId = sessionId,
                    lastMessage = content,
                    lastMessageAt = messageAtMillis,
                )
            )
        } else {
            chatHistoryDao.insertOrReplace(
                ChatHistoryEntity(
                    deviceId = peerDeviceId,
                    nickname = friend?.nickname ?: "未知用户",
                    avatar = friend?.avatar,
                    tags = friend?.tags ?: "[]",
                    profile = friend?.profile.orEmpty(),
                    isAnonymous = friend?.isAnonymous ?: false,
                    isFriend = friend != null,
                    sessionId = sessionId,
                    lastMessage = content,
                    lastMessageAt = messageAtMillis,
                    firstSeenAt = messageAtMillis,
                    lastSeenAt = messageAtMillis,
                )
            )
        }

        if (friend != null) {
            friendDao.insertOrReplace(
                friend.copy(
                    sessionId = sessionId,
                    lastChatAt = messageAtMillis,
                )
            )
        }
    }

    private suspend fun updateChatHistoryPreview(peerDeviceId: String, content: String) {
        chatHistoryDao.getByDeviceId(peerDeviceId)?.let { history ->
            chatHistoryDao.insertOrReplace(
                history.copy(
                    lastMessage = content,
                    lastMessageAt = System.currentTimeMillis(),
                )
            )
        }
    }

    private fun parseIsoToMillis(iso: String): Long {
        return try {
            Instant.parse(iso).toEpochMilli()
        } catch (_: Exception) {
            try {
                OffsetDateTime.parse(iso).toInstant().toEpochMilli()
            } catch (_: Exception) {
                try {
                    LocalDateTime.parse(iso, DateTimeFormatter.ISO_DATE_TIME)
                        .toInstant(ZoneOffset.UTC)
                        .toEpochMilli()
                } catch (_: Exception) {
                    System.currentTimeMillis()
                }
            }
        }
    }
}
