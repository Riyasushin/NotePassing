package com.example.notepassingapp.ui.chat

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.local.entity.MessageEntity
import com.example.notepassingapp.data.local.entity.FriendRequestDirection
import com.example.notepassingapp.data.model.FriendRequestState
import com.example.notepassingapp.data.model.visibleAvatar
import com.example.notepassingapp.data.model.visibleNickname
import com.example.notepassingapp.data.repository.AlreadyFriendsException
import com.example.notepassingapp.data.repository.FriendRequestAlreadyPendingException
import com.example.notepassingapp.data.repository.RelationRepository
import com.example.notepassingapp.data.repository.MessageRepository
import com.example.notepassingapp.util.DeviceManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ChatUiState(
    val peerDeviceId: String = "",
    val peerNickname: String = "",
    val peerAvatar: String? = null,
    val isFriend: Boolean = false,
    val isSessionExpired: Boolean = false,
    val friendRequestState: FriendRequestState = FriendRequestState.NONE,
    val isFriendActionLoading: Boolean = false,
    val friendStatusMessage: String? = null,
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
    private val friendRequestDao = db.friendRequestDao()
    private val chatHistoryDao = db.chatHistoryDao()
    private val myDeviceId = DeviceManager.getDeviceId()
    private val optimisticOutgoingPending = MutableStateFlow(false)

    private val _uiState = MutableStateFlow(ChatUiState(peerDeviceId = peerDeviceId))
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    val messages: StateFlow<List<MessageEntity>> = messageDao
        .getByPeer(myDeviceId, peerDeviceId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    init {
        observePeerInfo()
        observeMessagesForLimit()
        syncOnEntry()
    }

    private fun observePeerInfo() {
        viewModelScope.launch {
            combine(
                friendDao.observeByDeviceId(peerDeviceId),
                chatHistoryDao.observeByDeviceId(peerDeviceId),
                friendRequestDao.observeByPeer(peerDeviceId),
                optimisticOutgoingPending,
            ) { friend, history, pendingRequest, hasOptimisticOutgoing ->
                arrayOf(friend, history, pendingRequest, hasOptimisticOutgoing)
            }.collect { values ->
                val friend = values[0] as com.example.notepassingapp.data.local.entity.FriendEntity?
                val history = values[1] as com.example.notepassingapp.data.local.entity.ChatHistoryEntity?
                val pendingRequest = values[2] as com.example.notepassingapp.data.local.entity.FriendRequestEntity?
                val hasOptimisticOutgoing = values[3] as Boolean
                val isFriend = friend != null
                val isAnonymous = history?.isAnonymous ?: false
                val nickname = visibleNickname(
                    nickname = friend?.nickname ?: history?.nickname,
                    isAnonymous = isAnonymous,
                    isFriend = isFriend,
                )
                val avatar = visibleAvatar(
                    avatar = friend?.avatar ?: history?.avatar,
                    isAnonymous = isAnonymous,
                    isFriend = isFriend,
                )
                val requestState = when {
                    isFriend -> FriendRequestState.NONE
                    pendingRequest?.direction == FriendRequestDirection.OUTGOING -> FriendRequestState.OUTGOING_PENDING
                    pendingRequest?.direction == FriendRequestDirection.INCOMING -> FriendRequestState.INCOMING_PENDING
                    hasOptimisticOutgoing -> FriendRequestState.OUTGOING_PENDING
                    else -> FriendRequestState.NONE
                }

                if (hasOptimisticOutgoing && (isFriend || pendingRequest?.direction == FriendRequestDirection.OUTGOING)) {
                    optimisticOutgoingPending.value = false
                }

                _uiState.update {
                    it.copy(
                        peerNickname = nickname,
                        peerAvatar = avatar,
                        isFriend = isFriend,
                        isSessionExpired = history?.isSessionExpired ?: false,
                        friendRequestState = requestState,
                        friendStatusMessage = when (requestState) {
                            FriendRequestState.OUTGOING_PENDING -> "好友申请已发送，等待对方处理"
                            FriendRequestState.INCOMING_PENDING -> "对方已向你发送好友申请，请到好友页处理"
                            FriendRequestState.NONE -> if (isFriend) null else it.friendStatusMessage
                        }
                    )
                }
                checkSendLimit()
            }
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

    /**
     * 进入聊天页时触发一次会话级消息同步（握手补漏）。
     * 用本地该会话最新消息的时间戳向服务器拉取增量消息。
     */
    private fun syncOnEntry() {
        viewModelScope.launch {
            RelationRepository.syncFriends()

            // 需要先知道 sessionId —— 从已有消息中获取
            val existingMessages = messages.value
            val sessionId = existingMessages.firstOrNull { it.sessionId != "pending" }?.sessionId
            if (sessionId != null) {
                try {
                    val count = MessageRepository.syncSessionMessages(sessionId)
                    if (count > 0) {
                        Log.d("ChatViewModel", "Synced $count messages for session $sessionId")
                    }
                } catch (e: Exception) {
                    Log.e("ChatViewModel", "Session sync failed", e)
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

    fun sendFriendRequest() {
        val state = _uiState.value
        if (state.isFriend || state.friendRequestState != FriendRequestState.NONE || state.isFriendActionLoading) {
            return
        }

        viewModelScope.launch {
            _uiState.update {
                it.copy(
                    isFriendActionLoading = true,
                    friendStatusMessage = null
                )
            }

            val result = RelationRepository.sendFriendRequest(peerDeviceId)
            val error = result.exceptionOrNull()

            if (result.isSuccess || error is FriendRequestAlreadyPendingException) {
                optimisticOutgoingPending.value = true
            }

            _uiState.update {
                it.copy(
                    isFriendActionLoading = false,
                    friendStatusMessage = when (error) {
                        is FriendRequestAlreadyPendingException -> error.message
                        is AlreadyFriendsException -> error.message
                        else -> error?.message ?: it.friendStatusMessage
                    }
                )
            }
        }
    }

    private suspend fun checkSendLimit() {
        // Check if session is expired (for non-friends)
        if (!_uiState.value.isFriend && _uiState.value.isSessionExpired) {
            _uiState.value = _uiState.value.copy(
                canSend = false,
                sendLimitMessage = "会话已过期，对方已离开蓝牙范围，无法发送消息"
            )
            return
        }
        
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
