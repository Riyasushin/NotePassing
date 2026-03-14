package com.example.notepassingapp.data.repository

import android.util.Log
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.local.entity.MessageEntity
import com.example.notepassingapp.data.remote.ApiClient
import com.example.notepassingapp.data.remote.dto.SendMessageRequest
import com.example.notepassingapp.data.remote.ws.WebSocketManager
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
     * 发送消息。
     * 1. 先存本地（status=sending）
     * 2. 尝试 WS 发送
     * 3. WS 不可用时降级 HTTP
     * 4. 全部失败则 status 留 sending，后续可重试
     *
     * @return 发送是否成功提交（不等于对方收到）
     */
    suspend fun sendMessage(
        peerDeviceId: String,
        sessionId: String,
        content: String,
        type: String = "common"
    ): Boolean {
        val myDeviceId = DeviceManager.getDeviceId()
        val localMsgId = UUID.randomUUID().toString()

        val entity = MessageEntity(
            messageId = localMsgId,
            sessionId = sessionId,
            senderId = myDeviceId,
            receiverId = peerDeviceId,
            content = content,
            type = type,
            status = "sending"
        )
        messageDao.insert(entity)

        updateChatHistoryPreview(peerDeviceId, sessionId, content)

        if (WebSocketManager.isConnected()) {
            WebSocketManager.sendChatMessage(peerDeviceId, content, type)
            messageDao.insert(entity.copy(status = "sent"))
            return true
        }

        return try {
            val request = SendMessageRequest(
                senderId = myDeviceId,
                receiverId = peerDeviceId,
                content = content,
                type = type
            )
            val response = ApiClient.messageApi.sendMessage(request)
            if (response.isSuccess) {
                val serverData = response.data!!
                messageDao.insert(entity.copy(
                    messageId = serverData.messageId,
                    sessionId = serverData.sessionId,
                    status = serverData.status
                ))
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

    private suspend fun updateChatHistoryPreview(
        peerDeviceId: String,
        sessionId: String,
        content: String
    ) {
        chatHistoryDao.getByDeviceId(peerDeviceId)?.let { history ->
            chatHistoryDao.insertOrReplace(
                history.copy(
                    lastMessage = content,
                    lastMessageAt = System.currentTimeMillis(),
                    sessionId = sessionId
                )
            )
        }
    }
}
