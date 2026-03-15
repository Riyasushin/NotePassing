package com.example.notepassingapp.ui.friends

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.local.entity.FriendEntity
import com.example.notepassingapp.data.local.entity.FriendRequestDirection
import com.example.notepassingapp.data.local.entity.FriendRequestEntity
import com.example.notepassingapp.data.repository.RelationRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class FriendsViewModel : ViewModel() {

    private val legacyTestFriendIds = listOf("test-001", "test-002", "test-003")

    private val friendDao = NotePassingApp.instance.database.friendDao()
    private val friendRequestDao = NotePassingApp.instance.database.friendRequestDao()

    private val _processingRequestIds = MutableStateFlow<Set<String>>(emptySet())
    val processingRequestIds: StateFlow<Set<String>> = _processingRequestIds.asStateFlow()
    private val _deletingFriendIds = MutableStateFlow<Set<String>>(emptySet())
    val deletingFriendIds: StateFlow<Set<String>> = _deletingFriendIds.asStateFlow()

    /**
     * 好友列表，按 last_chat_at 排序（DAO 中已定义）。
     * stateIn 把 Flow 转为 StateFlow，供 Compose collectAsState 使用。
     * WhileSubscribed(5000)：UI 不可见 5 秒后停止收集，节省资源。
     */
    val friends: StateFlow<List<FriendEntity>> = friendDao.getAll()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )

    val incomingRequests: StateFlow<List<FriendRequestEntity>> = friendRequestDao
        .getByDirection(FriendRequestDirection.INCOMING)
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )

    init {
        purgeLegacyTestFriends()
        viewModelScope.launch {
            RelationRepository.syncFriends()
        }
        startPendingRequestPolling()
    }

    fun refreshIncomingRequests() {
        viewModelScope.launch {
            RelationRepository.syncIncomingFriendRequests()
        }
    }

    fun acceptFriendRequest(requestId: String) {
        handleFriendRequestAction(requestId, accept = true)
    }

    fun rejectFriendRequest(requestId: String) {
        handleFriendRequestAction(requestId, accept = false)
    }

    fun deleteFriend(friendDeviceId: String) {
        if (friendDeviceId in _deletingFriendIds.value) return

        viewModelScope.launch {
            _deletingFriendIds.update { it + friendDeviceId }
            try {
                RelationRepository.deleteFriend(friendDeviceId)
                RelationRepository.syncFriends()
            } finally {
                _deletingFriendIds.update { it - friendDeviceId }
            }
        }
    }

    private fun handleFriendRequestAction(requestId: String, accept: Boolean) {
        if (requestId in _processingRequestIds.value) return

        viewModelScope.launch {
            _processingRequestIds.update { it + requestId }
            try {
                RelationRepository.respondFriendRequest(requestId, accept)
                RelationRepository.syncIncomingFriendRequests()
                RelationRepository.syncFriends()
            } finally {
                _processingRequestIds.update { it - requestId }
            }
        }
    }

    private fun startPendingRequestPolling() {
        viewModelScope.launch {
            while (isActive) {
                RelationRepository.syncFriends()
                RelationRepository.syncIncomingFriendRequests()
                delay(3000)
            }
        }
    }

    private fun purgeLegacyTestFriends() {
        viewModelScope.launch {
            legacyTestFriendIds.forEach { friendDao.delete(it) }
        }
    }
}
