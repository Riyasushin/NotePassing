package com.example.notepassingapp.ui.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.local.entity.MessageEntity
import com.example.notepassingapp.util.DeviceManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.util.UUID

data class ChatUiState(
    val peerDeviceId: String = "",
    val peerNickname: String = "",
    val isFriend: Boolean = false,
    val inputText: String = "",
    val canSend: Boolean = true,
    val sendLimitMessage: String? = null  // 非好友超 2 条时的提示
)

/**
 * 聊天页 ViewModel。
 * 通过 peerDeviceId 区分不同聊天对象。
 * sessionId 用于消息分组（Phase 7 接入服务器后由服务器生成，目前本地模拟）。
 */
class ChatViewModel(
    private val peerDeviceId: String
) : ViewModel() {

    private val db = NotePassingApp.instance.database
    private val messageDao = db.messageDao()
    private val friendDao = db.friendDao()
    private val chatHistoryDao = db.chatHistoryDao()
    private val myDeviceId = DeviceManager.getDeviceId()

    // 用 peerDeviceId 作为临时 sessionId（后续由服务器分配）
    private val sessionId = "local-session-$peerDeviceId"

    private val _uiState = MutableStateFlow(ChatUiState(peerDeviceId = peerDeviceId))
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    val messages: StateFlow<List<MessageEntity>> = messageDao
        .getBySessionId(sessionId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    init {
        loadPeerInfo()
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

    fun updateInput(text: String) {
        _uiState.value = _uiState.value.copy(inputText = text)
    }

    fun sendMessage() {
        val text = _uiState.value.inputText.trim()
        if (text.isBlank()) return

        viewModelScope.launch {
            val entity = MessageEntity(
                messageId = UUID.randomUUID().toString(),
                sessionId = sessionId,
                senderId = myDeviceId,
                receiverId = peerDeviceId,
                content = text,
                type = "common",
                status = "sent"
            )
            messageDao.insert(entity)
            _uiState.value = _uiState.value.copy(inputText = "")

            // 更新 chat_history 中的最后消息预览
            chatHistoryDao.getByDeviceId(peerDeviceId)?.let { history ->
                chatHistoryDao.insertOrReplace(
                    history.copy(
                        lastMessage = text,
                        lastMessageAt = System.currentTimeMillis(),
                        sessionId = sessionId
                    )
                )
            }

            checkSendLimit()
        }
    }

    /** 非好友：未回复前最多发 2 条 */
    private suspend fun checkSendLimit() {
        if (_uiState.value.isFriend) {
            _uiState.value = _uiState.value.copy(canSend = true, sendLimitMessage = null)
            return
        }
        val myCount = messageDao.countMySentMessages(sessionId, myDeviceId)
        if (myCount >= 2) {
            _uiState.value = _uiState.value.copy(
                canSend = false,
                sendLimitMessage = "对方回复前最多发送 2 条消息"
            )
        }
    }

    /**
     * ViewModelProvider.Factory：让 Navigation 能传参数创建 ViewModel。
     * 因为 ViewModel 默认只有无参构造，我们需要传 peerDeviceId。
     */
    class Factory(private val peerDeviceId: String) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return ChatViewModel(peerDeviceId) as T
        }
    }
}
