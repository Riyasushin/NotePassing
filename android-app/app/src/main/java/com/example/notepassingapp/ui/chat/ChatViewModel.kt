package com.example.notepassingapp.ui.chat

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.local.entity.MessageEntity
import com.example.notepassingapp.data.remote.ws.WebSocketManager
import com.example.notepassingapp.data.remote.ws.WsNewMessagePayload
import com.example.notepassingapp.data.remote.ws.WsTypes
import com.example.notepassingapp.data.repository.MessageRepository
import com.example.notepassingapp.util.DeviceManager
import com.google.gson.Gson
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class ChatUiState(
    val peerDeviceId: String = "",
    val peerNickname: String = "",
    val isFriend: Boolean = false,
    val inputText: String = "",
    val canSend: Boolean = true,
    val sendLimitMessage: String? = null
)

class ChatViewModel(
    private val peerDeviceId: String
) : ViewModel() {

    private val db = NotePassingApp.instance.database
    private val messageDao = db.messageDao()
    private val friendDao = db.friendDao()
    private val chatHistoryDao = db.chatHistoryDao()
    private val myDeviceId = DeviceManager.getDeviceId()
    private val gson = Gson()

    private val _uiState = MutableStateFlow(ChatUiState(peerDeviceId = peerDeviceId))
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    val messages: StateFlow<List<MessageEntity>> = messageDao
        .getByPeer(myDeviceId, peerDeviceId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    init {
        loadPeerInfo()
        listenForIncomingMessages()
    }

    private fun loadPeerInfo() {
        viewModelScope.launch {
            val friend = friendDao.getByDeviceId(peerDeviceId)
            val history = chatHistoryDao.getByDeviceId(peerDeviceId)
            val nickname = friend?.nickname ?: history?.nickname ?: "未知用户"
            val isFriend = friend != null

            _uiState.value = _uiState.value.copy(
                peerNickname = nickname,
                isFriend = isFriend
            )
            checkSendLimit()
        }
    }

    /**
     * 监听 WebSocket 推送：如果收到来自当前聊天对象的消息，存入本地 Room。
     * Room 的 Flow 会自动触发 UI 更新。
     */
    private fun listenForIncomingMessages() {
        viewModelScope.launch {
            WebSocketManager.incomingMessages.collect { msg ->
                if (msg.type == WsTypes.NEW_MESSAGE && msg.payload != null) {
                    try {
                        val payload = gson.fromJson(msg.payload, WsNewMessagePayload::class.java)
                        if (payload.senderId == peerDeviceId) {
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

                            chatHistoryDao.getByDeviceId(peerDeviceId)?.let { history ->
                                chatHistoryDao.insertOrReplace(
                                    history.copy(
                                        lastMessage = payload.content,
                                        lastMessageAt = System.currentTimeMillis()
                                    )
                                )
                            }

                            checkSendLimit()
                        }
                    } catch (e: Exception) {
                        Log.e("ChatViewModel", "Failed to handle incoming message", e)
                    }
                }
            }
        }
    }

    fun updateInput(text: String) {
        _uiState.value = _uiState.value.copy(inputText = text)
    }

    fun sendMessage() {
        val text = _uiState.value.inputText.trim()
        if (text.isBlank()) return
        _uiState.value = _uiState.value.copy(inputText = "")

        viewModelScope.launch {
            MessageRepository.sendMessage(
                peerDeviceId = peerDeviceId,
                content = text
            )
            checkSendLimit()
        }
    }

    private suspend fun checkSendLimit() {
        if (_uiState.value.isFriend) {
            _uiState.value = _uiState.value.copy(canSend = true, sendLimitMessage = null)
            return
        }
        val myCount = messageDao.countMySentToPeer(myDeviceId, peerDeviceId)
        if (myCount >= 2) {
            _uiState.value = _uiState.value.copy(
                canSend = false,
                sendLimitMessage = "对方回复前最多发送 2 条消息"
            )
        }
    }

    class Factory(private val peerDeviceId: String) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return ChatViewModel(peerDeviceId) as T
        }
    }
}
