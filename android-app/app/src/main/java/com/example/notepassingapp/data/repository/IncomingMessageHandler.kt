package com.example.notepassingapp.data.repository

import android.util.Log
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.local.entity.MessageEntity
import com.example.notepassingapp.data.remote.ws.WebSocketManager
import com.example.notepassingapp.data.remote.ws.WsNewMessagePayload
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
 */
object IncomingMessageHandler {

    private const val TAG = "IncomingMsgHandler"
    private val gson = Gson()
    private var job: Job? = null

    fun start(scope: CoroutineScope) {
        if (job?.isActive == true) return

        val db = NotePassingApp.instance.database
        val messageDao = db.messageDao()
        val chatHistoryDao = db.chatHistoryDao()
        val myDeviceId = DeviceManager.getDeviceId()

        job = scope.launch {
            WebSocketManager.incomingMessages.collect { msg ->
                when (msg.type) {
                    WsTypes.NEW_MESSAGE -> handleNewMessage(
                        msg, myDeviceId, messageDao, chatHistoryDao
                    )
                }
            }
        }
        Log.d(TAG, "Global message listener started")
    }

    fun stop() {
        job?.cancel()
        job = null
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

            val entity = MessageEntity(
                messageId = payload.messageId,
                sessionId = payload.sessionId,
                senderId = payload.senderId,
                receiverId = myDeviceId,
                content = payload.content,
                type = payload.type,
                status = "received"
            )
            messageDao.insert(entity)

            chatHistoryDao.getByDeviceId(payload.senderId)?.let { history ->
                chatHistoryDao.insertOrReplace(
                    history.copy(
                        lastMessage = payload.content,
                        lastMessageAt = System.currentTimeMillis()
                    )
                )
            }

            Log.d(TAG, "Saved incoming msg ${payload.messageId} from ${payload.senderId}")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to handle new_message", e)
        }
    }
}
