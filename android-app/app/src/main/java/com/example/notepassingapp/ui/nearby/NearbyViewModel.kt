package com.example.notepassingapp.ui.nearby

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.ble.BleManager
import com.example.notepassingapp.ble.BleForegroundService
import com.example.notepassingapp.data.local.entity.ChatHistoryEntity
import com.example.notepassingapp.data.model.NearbyState
import com.example.notepassingapp.data.model.NearbyUser
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

class NearbyViewModel(application: Application) : AndroidViewModel(application) {

    private val chatHistoryDao = NotePassingApp.instance.database.chatHistoryDao()

    private val _realtimeStates = MutableStateFlow<Map<String, RealtimeState>>(emptyMap())

    val bleState = BleManager.state

    data class RealtimeState(
        val state: NearbyState = NearbyState.ACTIVE,
        val rssi: Int = -70,
        val distanceEstimate: Float = 3f,
        val leftAt: Long? = null
    )

    init {
        observeBleUpdates()
    }

    val nearbyUsers: StateFlow<List<NearbyUser>> = chatHistoryDao
        .getAllExcludeBlocked()
        .combine(_realtimeStates) { historyList, states ->
            historyList
                .map { entity -> entity.toNearbyUser(states[entity.deviceId]) }
                .filter { it.state != NearbyState.EXPIRED }
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
                        if (id !in newStates && rt.state == NearbyState.ACTIVE) {
                            val leftAt = rt.leftAt ?: now
                            if (now - leftAt < 60_000) {
                                merged[id] = rt.copy(state = NearbyState.GRACE, leftAt = leftAt)
                            } else {
                                merged[id] = rt.copy(state = NearbyState.EXPIRED)
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
        BleForegroundService.start(getApplication())
    }

    fun stopBle() {
        BleForegroundService.stop(getApplication())
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

    private suspend fun ChatHistoryEntity.toNearbyUser(rt: RealtimeState?): NearbyUser {
        val effectiveState = if (isSessionExpired && !isFriend) {
            // Session expired non-friends are always EXPIRED
            NearbyState.EXPIRED
        } else {
            rt?.state ?: run {
                val elapsed = System.currentTimeMillis() - lastSeenAt
                when {
                    elapsed < 10_000 -> NearbyState.ACTIVE
                    elapsed < 60_000 -> NearbyState.GRACE
                    else -> NearbyState.EXPIRED
                }
            }
        }
        return NearbyUser(
            deviceId = deviceId,
            nickname = nickname,
            avatar = avatar,
            profile = profile,
            isAnonymous = isAnonymous,
            roleName = roleName,
            isFriend = isFriend,
            state = effectiveState,
            rssi = rt?.rssi ?: -100,
            distanceEstimate = rt?.distanceEstimate ?: 0f,
            leftAt = rt?.leftAt,
            sessionId = sessionId,
            lastMessage = lastMessage,
            lastMessageAt = lastMessageAt
        )
    }

    // ---- 测试用，后续删除 ----
    fun insertTestData() {
        viewModelScope.launch {
            val now = System.currentTimeMillis()
            val testUsers = listOf(
                ChatHistoryEntity(
                    deviceId = "nearby-001",
                    nickname = "小红",
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
                    profile = "路过的旅行者",
                    isFriend = false,
                    lastSeenAt = now,
                    firstSeenAt = now - 300_000
                ),
                ChatHistoryEntity(
                    deviceId = "nearby-003",
                    nickname = "老王",
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
