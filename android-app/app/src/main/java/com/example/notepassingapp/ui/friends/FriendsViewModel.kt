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

    private val friendDao = NotePassingApp.instance.database.friendDao()
    private val friendRequestDao = NotePassingApp.instance.database.friendRequestDao()

    private val _processingRequestIds = MutableStateFlow<Set<String>>(emptySet())
    val processingRequestIds: StateFlow<Set<String>> = _processingRequestIds.asStateFlow()

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
                RelationRepository.syncIncomingFriendRequests()
                delay(3000)
            }
        }
    }

    // ---- 测试用，后续删除 ----
    fun insertTestFriends() {
        viewModelScope.launch {
            val now = System.currentTimeMillis()
            val testFriends = listOf(
                FriendEntity(
                    deviceId = "test-001",
                    nickname = "小明",
                    profile = "喜欢拍照的程序员",
                    tags = "[\"摄影\",\"编程\"]",
                    meetCount = 5,
                    isNearby = true,
                    isAnonymous = true,
                    lastChatAt = now - 300_000,   // 5 分钟前
                    createdAt = now - 86400_000
                ),
                FriendEntity(
                    deviceId = "test-002",
                    nickname = "Alice",
                    profile = "旅行中...",
                    tags = "[\"旅行\",\"音乐\"]",
                    meetCount = 2,
                    isNearby = false,
                    isAnonymous = true,
                    lastChatAt = now - 3600_000,  // 1 小时前
                    createdAt = now - 172800_000
                ),
                FriendEntity(
                    deviceId = "test-003",
                    nickname = "神秘旅者",
                    profile = "",
                    isAnonymous = true,
                    meetCount = 0,
                    isNearby = false,
                    lastChatAt = null,
                    createdAt = now - 7200_000
                )
            )
            testFriends.forEach { friendDao.insertOrReplace(it) }
        }
    }

    fun clearTestFriends() {
        viewModelScope.launch {
            listOf("test-001", "test-002", "test-003").forEach {
                friendDao.delete(it)
            }
        }
    }
    // ---- 测试用结束 ----
}
