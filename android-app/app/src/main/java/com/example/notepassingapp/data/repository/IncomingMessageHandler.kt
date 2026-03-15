package com.example.notepassingapp.data.repository

import android.util.Log
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.local.entity.MessageEntity
import com.example.notepassingapp.data.remote.ws.WebSocketManager
import com.example.notepassingapp.data.remote.ws.WsFriendDeletedPayload
import com.example.notepassingapp.data.remote.ws.WsFriendRequestPayload
import com.example.notepassingapp.data.remote.ws.WsFriendResponsePayload
import com.example.notepassingapp.data.remote.ws.WsNewMessagePayload
import com.example.notepassingapp.data.remote.ws.WsSessionExpiredPayload
import com.example.notepassingapp.data.remote.ws.WsTypes
import com.example.notepassingapp.util.DeviceManager
import com.google.gson.Gson
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

/**
 * App 级别的全局 WS 消息接收器。
 * 不管用户在哪个页面，所有 new_message 都会写入 Room。
 * Room 的 Flow 会自动通知任何正在订阅的 UI。
 *
 * 同时监听 WS 连接状态，重连成功后自动触发全局消息同步（握手补漏）。
 */
object IncomingMessageHandler {

    private const val TAG = "IncomingMsgHandler"
    private val gson = Gson()
    private var messageJob: Job? = null
    private var syncJob: Job? = null

    fun start(scope: CoroutineScope) {
        startMessageListener(scope)
        startReconnectSyncListener(scope)
    }

    fun stop() {
        messageJob?.cancel()
        messageJob = null
        syncJob?.cancel()
        syncJob = null
    }

    private fun startMessageListener(scope: CoroutineScope) {
        if (messageJob?.isActive == true) return

        val db = NotePassingApp.instance.database
        val messageDao = db.messageDao()
        val chatHistoryDao = db.chatHistoryDao()
        val myDeviceId = DeviceManager.getDeviceId()

        messageJob = scope.launch {
            WebSocketManager.incomingMessages.collect { msg ->
                when (msg.type) {
                    WsTypes.NEW_MESSAGE -> handleNewMessage(
                        msg, myDeviceId, messageDao, chatHistoryDao
                    )
                    WsTypes.FRIEND_REQUEST -> handleFriendRequest(msg)
                    WsTypes.FRIEND_RESPONSE -> handleFriendResponse(msg)
                    WsTypes.FRIEND_DELETED -> handleFriendDeleted(msg)
                    WsTypes.SESSION_EXPIRED -> handleSessionExpired(
                        msg, chatHistoryDao
                    )
                }
            }
        }
        Log.d(TAG, "Global message listener started")
    }

    /**
     * 监听 WS 连接状态，每次从非连接态变为 CONNECTED 时触发全局消息同步。
     * 这是消息握手机制的核心：WS 重连后，用本地最新时间戳向服务器拉取增量消息。
     */
    private fun startReconnectSyncListener(scope: CoroutineScope) {
        if (syncJob?.isActive == true) return

        var wasConnected = false

        syncJob = scope.launch {
            WebSocketManager.connectionState.collect { state ->
                if (state == WebSocketManager.ConnectionState.CONNECTED) {
                    if (!wasConnected) {
                        // 首次连接或重连成功 → 触发全局同步
                        Log.d(TAG, "WS connected/reconnected — triggering message sync")
                        try {
                            val count = MessageRepository.syncAllMessages()
                            Log.d(TAG, "Reconnect sync completed: $count new messages")
                            RelationRepository.syncFriends()
                            RelationRepository.syncIncomingFriendRequests()
                        } catch (e: Exception) {
                            Log.e(TAG, "Reconnect sync failed", e)
                        }
                    }
                    wasConnected = true
                } else if (state == WebSocketManager.ConnectionState.DISCONNECTED ||
                           state == WebSocketManager.ConnectionState.RECONNECTING) {
                    wasConnected = false
                }
            }
        }
        Log.d(TAG, "Reconnect sync listener started")
    }

    private suspend fun handleNewMessage(
        msg: com.example.notepassingapp.data.remote.ws.WsServerMessage,
        myDeviceId: String,
        messageDao: com.example.notepassingapp.data.local.dao.MessageDao,
        chatHistoryDao: com.example.notepassingapp.data.local.dao.ChatHistoryDao,
    ) {
        if (msg.payload == null) return
        try {
            val payload = gson.fromJson(msg.payload, WsNewMessagePayload::class.java)
            val createdAtMillis = MessageRepository.parseServerTimestamp(payload.createdAt)

            val entity = MessageEntity(
                messageId = payload.messageId,
                sessionId = payload.sessionId,
                senderId = payload.senderId,
                receiverId = myDeviceId,
                content = payload.content,
                type = payload.type,
                status = "received",
                createdAt = createdAtMillis,
            )
            messageDao.insert(entity)
            MessageRepository.upsertConversationState(
                peerDeviceId = payload.senderId,
                sessionId = payload.sessionId,
                content = payload.content,
                messageAtMillis = createdAtMillis,
            )

            Log.d(TAG, "Saved incoming msg ${payload.messageId} from ${payload.senderId}")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to handle new_message", e)
        }
    }
    
    private suspend fun handleSessionExpired(
        msg: com.example.notepassingapp.data.remote.ws.WsServerMessage,
        chatHistoryDao: com.example.notepassingapp.data.local.dao.ChatHistoryDao,
    ) {
        if (msg.payload == null) return
        try {
            val payload = gson.fromJson(msg.payload, WsSessionExpiredPayload::class.java)
            
            // Mark the chat session as expired
            chatHistoryDao.markSessionExpired(payload.peerDeviceId)
            
            Log.d(TAG, "Session expired for peer: ${payload.peerDeviceId}, reason: ${payload.reason}")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to handle session_expired", e)
        }
    }

    private suspend fun handleFriendRequest(
        msg: com.example.notepassingapp.data.remote.ws.WsServerMessage,
    ) {
        if (msg.payload == null) return
        try {
            val payload = gson.fromJson(msg.payload, WsFriendRequestPayload::class.java)
            RelationRepository.saveIncomingFriendRequest(payload)
            Log.d(TAG, "Saved incoming friend request ${payload.requestId}")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to handle friend_request", e)
        }
    }

    private suspend fun handleFriendResponse(
        msg: com.example.notepassingapp.data.remote.ws.WsServerMessage,
    ) {
        if (msg.payload == null) return
        try {
            val payload = gson.fromJson(msg.payload, WsFriendResponsePayload::class.java)
            RelationRepository.handleFriendResponse(payload)
            Log.d(TAG, "Handled friend response ${payload.requestId} status=${payload.status}")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to handle friend_response", e)
        }
    }

    private suspend fun handleFriendDeleted(
        msg: com.example.notepassingapp.data.remote.ws.WsServerMessage,
    ) {
        if (msg.payload == null) return
        try {
            val payload = gson.fromJson(msg.payload, WsFriendDeletedPayload::class.java)
            RelationRepository.handleFriendDeleted(payload)
            Log.d(TAG, "Handled friend_deleted for ${payload.peerDeviceId}")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to handle friend_deleted", e)
        }
    }
}
