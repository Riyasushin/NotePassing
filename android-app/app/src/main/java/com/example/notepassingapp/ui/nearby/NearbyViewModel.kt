package com.example.notepassingapp.ui.nearby

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.local.entity.ChatHistoryEntity
import com.example.notepassingapp.data.model.NearbyState
import com.example.notepassingapp.data.model.NearbyUser
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class NearbyViewModel : ViewModel() {

    private val chatHistoryDao = NotePassingApp.instance.database.chatHistoryDao()

    /**
     * 内存中的实时状态表：deviceId → (NearbyState, rssi, leftAt)
     * Phase 8/9 中 BLE 扫描和心跳会更新此表。
     * 目前用测试数据模拟。
     */
    private val _realtimeStates = MutableStateFlow<Map<String, RealtimeState>>(emptyMap())

    data class RealtimeState(
        val state: NearbyState = NearbyState.ACTIVE,
        val rssi: Int = -70,
        val distanceEstimate: Float = 3f,
        val leftAt: Long? = null
    )

    /**
     * 附近页数据：chat_history + 实时状态 → 过滤 + 排序
     * combine：两个 Flow 中任一变化都会重新计算
     */
    val nearbyUsers: StateFlow<List<NearbyUser>> = chatHistoryDao
        .getAllExcludeBlocked()
        .combine(_realtimeStates) { historyList, states ->
            historyList
                .map { entity -> entity.toNearbyUser(states[entity.deviceId]) }
                .filter { it.state != NearbyState.EXPIRED }
                .sortedWith(nearbyComparator())
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    /**
     * 排序规则（对应 local_structure_v2.md §7）：
     * 1. active 好友（rssi 强→弱）
     * 2. active 非好友（rssi 强→弱）
     * 3. grace 好友（离开时间短→长）
     * 4. grace 非好友（离开时间短→长）
     */
    private fun nearbyComparator(): Comparator<NearbyUser> = compareBy<NearbyUser> { user ->
        when {
            user.state == NearbyState.ACTIVE && user.isFriend -> 0
            user.state == NearbyState.ACTIVE && !user.isFriend -> 1
            user.state == NearbyState.GRACE && user.isFriend -> 2
            else -> 3
        }
    }.thenByDescending { it.rssi }   // rssi 越大（越接近0）越近
     .thenBy { it.leftAt ?: Long.MAX_VALUE }  // grace 态按离开时间排

    private fun ChatHistoryEntity.toNearbyUser(rt: RealtimeState?): NearbyUser {
        val effectiveState = rt?.state ?: run {
            val elapsed = System.currentTimeMillis() - lastSeenAt
            when {
                elapsed < 10_000 -> NearbyState.ACTIVE
                elapsed < 60_000 -> NearbyState.GRACE
                else -> NearbyState.EXPIRED
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
                    lastSeenAt = now - 30_000, // 30 秒前离开 → grace
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
                    lastSeenAt = now - 45_000, // 45 秒前 → grace
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
    // ---- 测试用结束 ----
}
