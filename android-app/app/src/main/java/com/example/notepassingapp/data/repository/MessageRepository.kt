package com.example.notepassingapp.data.repository

import android.util.Log
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.local.entity.MessageEntity
import com.example.notepassingapp.data.remote.ApiClient
import com.example.notepassingapp.data.remote.dto.SendMessageRequest
import com.example.notepassingapp.util.DeviceManager
import java.util.UUID

/**
 * 消息仓库：WebSocket 优先发送，失败时降级到 HTTP。
 * 同时维护本地 Room 数据库。
 */
object MessageRepository {

    private const val TAG = "MessageRepository"
    private val messageDao = NotePassingApp.instance.database.messageDao()
    private val chatHistoryDao = NotePassingApp.instance.database.chatHistoryDao()

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
                messageDao.delete(localMsgId)
                messageDao.insert(entity.copy(
                    messageId = data.messageId,
                    sessionId = data.sessionId,
                    status = data.status
                ))
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

    private suspend fun updateChatHistoryPreview(peerDeviceId: String, content: String) {
        chatHistoryDao.getByDeviceId(peerDeviceId)?.let { history ->
            chatHistoryDao.insertOrReplace(
                history.copy(
                    lastMessage = content,
                    lastMessageAt = System.currentTimeMillis()
                )
            )
        }
    }
}
