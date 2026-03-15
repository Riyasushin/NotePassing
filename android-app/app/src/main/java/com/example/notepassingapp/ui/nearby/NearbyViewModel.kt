package com.example.notepassingapp.ui.nearby

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.ble.BleManager
import com.example.notepassingapp.ble.BleForegroundService
import com.example.notepassingapp.data.local.entity.ChatHistoryEntity
import com.example.notepassingapp.data.local.entity.FriendRequestDirection
import com.example.notepassingapp.data.model.FriendRequestState
import com.example.notepassingapp.data.model.NearbyState
import com.example.notepassingapp.data.model.NearbyUser
import com.example.notepassingapp.data.model.shouldHideIdentity
import com.example.notepassingapp.data.model.visibleAvatar
import com.example.notepassingapp.data.model.visibleNickname
import com.example.notepassingapp.data.model.visibleProfile
import com.example.notepassingapp.data.model.visibleTags
import com.example.notepassingapp.notifications.TagMatchAlert
import com.example.notepassingapp.data.repository.FriendRequestAlreadyPendingException
import com.example.notepassingapp.data.repository.RelationRepository
import com.example.notepassingapp.ui.components.ProfilePreviewData
import com.example.notepassingapp.util.DeviceManager
import com.example.notepassingapp.util.TagSerializer
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class NearbyViewModel(application: Application) : AndroidViewModel(application) {

    private val chatHistoryDao = NotePassingApp.instance.database.chatHistoryDao()
    private val friendRequestDao = NotePassingApp.instance.database.friendRequestDao()

    private val _realtimeStates = MutableStateFlow<Map<String, RealtimeState>>(emptyMap())
    private val _processingRequestIds = MutableStateFlow<Set<String>>(emptySet())
    private val _processingBlockIds = MutableStateFlow<Set<String>>(emptySet())
    private val _tagMatchCards = MutableStateFlow<List<TagMatchCardUiState>>(emptyList())
    private val _optimisticOutgoingRequestIds = MutableStateFlow<Set<String>>(emptySet())
    private var hasTriedAutoStart = false

    val bleState = BleManager.state
    val processingRequestIds: StateFlow<Set<String>> = _processingRequestIds.asStateFlow()
    val processingBlockIds: StateFlow<Set<String>> = _processingBlockIds.asStateFlow()
    val tagMatchCards: StateFlow<List<TagMatchCardUiState>> = _tagMatchCards.asStateFlow()

    data class RealtimeState(
        val state: NearbyState = NearbyState.ACTIVE,
        val rssi: Int = -70,
        val distanceEstimate: Float = 3f,
        val leftAt: Long? = null
    )

    init {
        observeBleUpdates()
        observeTagMatchAlerts()
        startGraceExpiryTicker()
    }

    val nearbyUsers: StateFlow<List<NearbyUser>> = combine(
        chatHistoryDao.getAllExcludeBlocked(),
        _realtimeStates,
        friendRequestDao.getAll(),
        _optimisticOutgoingRequestIds,
    ) { historyList, states, pendingRequests, optimisticOutgoingRequestIds ->
            val pendingByPeer = pendingRequests.associateBy { it.peerDeviceId }
            historyList
                .map { entity ->
                    entity.toNearbyUser(
                        rt = states[entity.deviceId],
                        friendRequestState = pendingByPeer[entity.deviceId].toFriendRequestState(
                            isFriend = entity.isFriend,
                            hasOptimisticOutgoing = entity.deviceId in optimisticOutgoingRequestIds,
                        )
                    )
                }
                .sortedWith(nearbyComparator())
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    private fun observeBleUpdates() {
        viewModelScope.launch {
            BleManager.nearbyUpdate.collect { event ->
                val now = System.currentTimeMillis()
                val newStates = event.resolved.associate { device ->
                    device.deviceId to RealtimeState(
                        state = NearbyState.ACTIVE,
                        rssi = device.rssi,
                        distanceEstimate = device.distanceEstimate
                    )
                }
                
                // Track non-friends who entered EXPIRED state to mark session expired
                val newlyExpiredNonFriends = mutableListOf<String>()
                
                _realtimeStates.update { current ->
                    val merged = current.toMutableMap()
                    
                    // Handle devices that left ACTIVE state (enter GRACE)
                    current.forEach { (id, rt) ->
                        if (id !in newStates && rt.state != NearbyState.EXPIRED) {
                            val leftAt = rt.leftAt ?: now
                            if (now - leftAt < 60_000) {
                                merged[id] = rt.copy(state = NearbyState.GRACE, leftAt = leftAt)
                            } else {
                                merged[id] = rt.copy(state = NearbyState.EXPIRED, leftAt = leftAt)
                                // Check if this is a non-friend entering EXPIRED
                                if (isNonFriend(id)) {
                                    newlyExpiredNonFriends.add(id)
                                }
                            }
                        }
                    }
                    
                    // Handle friends who completely left the range (from BleManager)
                    event.leftFriendIds.forEach { leftId ->
                        merged[leftId] = RealtimeState(
                            state = NearbyState.EXPIRED,
                            rssi = -100,
                            distanceEstimate = 0f,
                            leftAt = now
                        )
                    }
                    
                    merged.putAll(newStates)
                    merged
                }
                
                // Mark sessions as expired for non-friends who entered EXPIRED state
                if (newlyExpiredNonFriends.isNotEmpty()) {
                    markNonFriendSessionsExpired(newlyExpiredNonFriends)
                }
            }
        }
    }

    private fun observeTagMatchAlerts() {
        viewModelScope.launch {
            BleManager.tagMatchAlerts.collect { alerts ->
                val cards = buildList {
                    alerts.forEach { alert ->
                        buildTagMatchCard(alert)?.let(::add)
                    }
                }
                if (cards.isEmpty()) return@collect

                _tagMatchCards.update { existing ->
                    val existingIds = existing.map { it.deviceId }.toSet()
                    existing + cards.filter { it.deviceId !in existingIds }
                }
            }
        }
    }

    private fun startGraceExpiryTicker() {
        viewModelScope.launch {
            while (isActive) {
                delay(1000)
                expireGraceUsers()
            }
        }
    }

    private suspend fun expireGraceUsers() {
        val now = System.currentTimeMillis()
        val expiredIds = _realtimeStates.value
            .filterValues { rt ->
                rt.state == NearbyState.GRACE &&
                    rt.leftAt != null &&
                    now - rt.leftAt >= 60_000
            }
            .keys

        if (expiredIds.isEmpty()) return

        _realtimeStates.update { current ->
            current.mapValues { (id, rt) ->
                if (id in expiredIds) {
                    rt.copy(state = NearbyState.EXPIRED)
                } else {
                    rt
                }
            }
        }

        val newlyExpiredNonFriends = expiredIds.filter { isNonFriend(it) }
        if (newlyExpiredNonFriends.isNotEmpty()) {
            markNonFriendSessionsExpired(newlyExpiredNonFriends)
        }
    }
    
    private suspend fun isNonFriend(deviceId: String): Boolean {
        val entity = chatHistoryDao.getByDeviceId(deviceId)
        return entity?.isFriend == false
    }
    
    private fun markNonFriendSessionsExpired(deviceIds: List<String>) {
        viewModelScope.launch {
            deviceIds.forEach { deviceId ->
                try {
                    chatHistoryDao.markSessionExpired(deviceId)
                    Log.d("NearbyViewModel", "Marked session expired for non-friend: $deviceId")
                } catch (e: Exception) {
                    Log.e("NearbyViewModel", "Failed to mark session expired for $deviceId", e)
                }
            }
        }
    }

    fun startBle() {
        hasTriedAutoStart = true
        BleForegroundService.start(getApplication())
    }

    fun stopBle() {
        hasTriedAutoStart = true
        BleForegroundService.stop(getApplication())
    }

    fun ensureBleRunningWhenReady(hasPermissions: Boolean) {
        if (!hasPermissions || bleState.value.running || hasTriedAutoStart) return
        hasTriedAutoStart = true
        BleForegroundService.start(getApplication())
    }

    fun sendFriendRequest(user: NearbyUser) {
        if (user.isFriend || user.friendRequestState != FriendRequestState.NONE) return
        if (user.deviceId in _processingRequestIds.value) return

        viewModelScope.launch {
            _processingRequestIds.update { it + user.deviceId }
            try {
                val result = RelationRepository.sendFriendRequest(user.deviceId)
                val error = result.exceptionOrNull()

                if (error is FriendRequestAlreadyPendingException) {
                    _optimisticOutgoingRequestIds.update { it + user.deviceId }
                }

                error?.let {
                    Log.e("NearbyViewModel", "Failed to send friend request to ${user.deviceId}", error)
                }
            } finally {
                _processingRequestIds.update { it - user.deviceId }
            }
        }
    }

    fun blockUser(user: NearbyUser) {
        if (user.deviceId in _processingBlockIds.value) return

        viewModelScope.launch {
            _processingBlockIds.update { it + user.deviceId }
            try {
                val success = RelationRepository.blockUser(user.deviceId)
                if (!success) {
                    Log.e("NearbyViewModel", "Failed to block user ${user.deviceId}")
                }
            } finally {
                _processingBlockIds.update { it - user.deviceId }
            }
        }
    }

    fun ignoreCurrentTagMatch() {
        _tagMatchCards.update { current ->
            if (current.isEmpty()) current else current.drop(1)
        }
    }

    fun clearAllTagMatches() {
        _tagMatchCards.value = emptyList()
    }

    private fun nearbyComparator(): Comparator<NearbyUser> = compareBy<NearbyUser> { user ->
        when {
            user.state == NearbyState.ACTIVE && user.isFriend -> 0
            user.state == NearbyState.ACTIVE && !user.isFriend -> 1
            user.state == NearbyState.GRACE && user.isFriend -> 2
            else -> 3
        }
    }.thenByDescending { it.rssi }
        .thenBy { it.leftAt ?: Long.MAX_VALUE }

    private suspend fun ChatHistoryEntity.toNearbyUser(
        rt: RealtimeState?,
        friendRequestState: FriendRequestState
    ): NearbyUser {
        val fallbackStateAndLeftAt = run {
            val elapsed = System.currentTimeMillis() - lastSeenAt
            when {
                elapsed < 10_000 -> NearbyState.ACTIVE to null
                elapsed < 60_000 -> NearbyState.GRACE to lastSeenAt
                else -> NearbyState.EXPIRED to lastSeenAt
            }
        }

        val effectiveState = if (isSessionExpired && !isFriend) {
            NearbyState.EXPIRED
        } else {
            rt?.state ?: fallbackStateAndLeftAt.first
        }

        val effectiveLeftAt = rt?.leftAt ?: when {
            effectiveState == NearbyState.GRACE -> fallbackStateAndLeftAt.second
            effectiveState == NearbyState.EXPIRED -> fallbackStateAndLeftAt.second
            else -> null
        }

        return NearbyUser(
            deviceId = deviceId,
            nickname = nickname,
            avatar = avatar,
            tags = TagSerializer.decode(tags),
            commonTags = TagSerializer.findCommonTags(DeviceManager.getTags(), TagSerializer.decode(tags)),
            profile = profile,
            isAnonymous = isAnonymous,
            roleName = roleName,
            isFriend = isFriend,
            state = effectiveState,
            rssi = rt?.rssi ?: -100,
            distanceEstimate = rt?.distanceEstimate ?: 0f,
            leftAt = effectiveLeftAt,
            friendRequestState = friendRequestState,
            sessionId = sessionId,
            lastMessage = lastMessage,
            lastMessageAt = lastMessageAt
        )
    }

    private suspend fun buildTagMatchCard(alert: TagMatchAlert): TagMatchCardUiState? {
        val history = chatHistoryDao.getByDeviceId(alert.deviceId)
        if (history == null) {
            return TagMatchCardUiState(
                deviceId = alert.deviceId,
                preview = ProfilePreviewData(
                    avatarUrl = null,
                    nickname = alert.nickname,
                    profile = "",
                    tags = emptyList(),
                    isFriend = false,
                    isIdentityHidden = false,
                ),
                commonTags = alert.commonTags,
            )
        }

        val isIdentityHidden = shouldHideIdentity(history.isAnonymous, history.isFriend)
        return TagMatchCardUiState(
            deviceId = alert.deviceId,
            preview = ProfilePreviewData(
                avatarUrl = visibleAvatar(history.avatar, history.isAnonymous, history.isFriend),
                nickname = visibleNickname(history.nickname, history.isAnonymous, history.isFriend),
                profile = visibleProfile(history.profile, history.isAnonymous, history.isFriend),
                tags = visibleTags(TagSerializer.decode(history.tags), history.isAnonymous, history.isFriend),
                isFriend = history.isFriend,
                isIdentityHidden = isIdentityHidden,
            ),
            commonTags = if (isIdentityHidden) emptyList() else alert.commonTags,
        )
    }

    private fun com.example.notepassingapp.data.local.entity.FriendRequestEntity?.toFriendRequestState(
        isFriend: Boolean,
        hasOptimisticOutgoing: Boolean = false,
    ): FriendRequestState {
        if (isFriend) return FriendRequestState.NONE
        return when (this?.direction) {
            FriendRequestDirection.OUTGOING -> FriendRequestState.OUTGOING_PENDING
            FriendRequestDirection.INCOMING -> FriendRequestState.INCOMING_PENDING
            else -> if (hasOptimisticOutgoing) FriendRequestState.OUTGOING_PENDING else FriendRequestState.NONE
        }
    }

    // ---- 测试用，后续删除 ----
    fun insertTestData() {
        viewModelScope.launch {
            val now = System.currentTimeMillis()
            val testUsers = listOf(
                ChatHistoryEntity(
                    deviceId = "nearby-001",
                    nickname = "小红",
                    tags = TagSerializer.encode(listOf("摄影", "咖啡")),
                    profile = "喜欢画画",
                    isFriend = true,
                    lastSeenAt = now,
                    firstSeenAt = now - 600_000,
                    lastMessage = "你好呀！",
                    lastMessageAt = now - 120_000
                ),
                ChatHistoryEntity(
                    deviceId = "nearby-002",
                    nickname = "路人甲",
                    tags = TagSerializer.encode(listOf("徒步", "摄影")),
                    profile = "路过的旅行者",
                    isFriend = false,
                    lastSeenAt = now,
                    firstSeenAt = now - 300_000
                ),
                ChatHistoryEntity(
                    deviceId = "nearby-003",
                    nickname = "老王",
                    tags = TagSerializer.encode(listOf("编程", "桌游")),
                    profile = "隔壁的程序员",
                    isFriend = true,
                    lastSeenAt = now - 30_000,
                    firstSeenAt = now - 900_000,
                    lastMessage = "下次见",
                    lastMessageAt = now - 35_000
                ),
                ChatHistoryEntity(
                    deviceId = "nearby-004",
                    nickname = "神秘人",
                    tags = TagSerializer.encode(listOf("夜跑")),
                    profile = "",
                    isAnonymous = true,
                    roleName = "夜行者",
                    isFriend = false,
                    lastSeenAt = now - 45_000,
                    firstSeenAt = now - 200_000
                )
            )
            testUsers.forEach { chatHistoryDao.insertOrReplace(it) }

            _realtimeStates.value = mapOf(
                "nearby-001" to RealtimeState(NearbyState.ACTIVE, rssi = -55, distanceEstimate = 1.5f),
                "nearby-002" to RealtimeState(NearbyState.ACTIVE, rssi = -72, distanceEstimate = 5f),
                "nearby-003" to RealtimeState(NearbyState.GRACE, rssi = -80, leftAt = now - 30_000),
                "nearby-004" to RealtimeState(NearbyState.GRACE, rssi = -85, leftAt = now - 45_000)
            )
        }
    }

    fun clearTestData() {
        viewModelScope.launch {
            listOf("nearby-001", "nearby-002", "nearby-003", "nearby-004").forEach {
                chatHistoryDao.delete(it)
            }
            _realtimeStates.value = emptyMap()
        }
    }
}
