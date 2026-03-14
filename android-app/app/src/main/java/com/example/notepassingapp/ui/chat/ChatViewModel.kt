package com.example.notepassingapp.ui.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.local.entity.MessageEntity
import com.example.notepassingapp.data.repository.MessageRepository
import com.example.notepassingapp.util.DeviceManager
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

    private val _uiState = MutableStateFlow(ChatUiState(peerDeviceId = peerDeviceId))
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    val messages: StateFlow<List<MessageEntity>> = messageDao
        .getByPeer(myDeviceId, peerDeviceId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    init {
        loadPeerInfo()
        observeMessagesForLimit()
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
     * 当 Room 中消息列表变化时（全局 Handler 写入、自己发送等），
     * 自动重新检查发送限制。
     */
    private fun observeMessagesForLimit() {
        viewModelScope.launch {
            messages.collect { checkSendLimit() }
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
        val peerCount = messageDao.countPeerSentToMe(peerDeviceId, myDeviceId)
        if (myCount >= 2 && peerCount == 0) {
            _uiState.value = _uiState.value.copy(
                canSend = false,
                sendLimitMessage = "对方回复前最多发送 2 条消息"
            )
        } else {
            _uiState.value = _uiState.value.copy(canSend = true, sendLimitMessage = null)
        }
    }

    class Factory(private val peerDeviceId: String) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return ChatViewModel(peerDeviceId) as T
        }
    }
}
