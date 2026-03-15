package com.example.notepassingapp.ble

import android.content.Context
import android.util.Log
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.local.entity.ChatHistoryEntity
import com.example.notepassingapp.data.remote.dto.ScannedDevice
import com.example.notepassingapp.notifications.FriendReunionAlert
import com.example.notepassingapp.notifications.FriendReunionNotifier
import com.example.notepassingapp.notifications.TagMatchAlert
import com.example.notepassingapp.notifications.TagMatchNotifier
import com.example.notepassingapp.data.repository.PresenceRepository
import com.example.notepassingapp.data.repository.TempIdRepository
import com.example.notepassingapp.util.DeviceManager
import com.example.notepassingapp.util.TagSerializer
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import java.text.SimpleDateFormat
import java.util.*

/**
 * BLE 总调度：管理 advertise / scan 周期、temp_id 刷新、
 * 扫描结果 → /presence/resolve → chat_history 写入。
 */
object BleManager {

    private const val TAG = "BleManager"
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private var advertiser: BleAdvertiser? = null
    private var scanner: BleScanner? = null
    private var scanLoopJob: Job? = null
    private var tempIdJob: Job? = null
    private var collectJob: Job? = null

    private val bleFindMap = Collections.synchronizedMap(mutableMapOf<String, BleFoundDevice>())
    private val tagMatchSignatures = Collections.synchronizedMap(mutableMapOf<String, String>())
    private val announcedTagMatchDeviceIds = Collections.synchronizedSet(mutableSetOf<String>())
    
    // Track which friends are currently nearby to handle leave events
    private val nearbyFriendIds = Collections.synchronizedSet(mutableSetOf<String>())

    // ---------- exposed state ----------

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    private val _nearbyUpdate = MutableSharedFlow<NearbyUpdateEvent>(extraBufferCapacity = 8)
    val nearbyUpdate: SharedFlow<NearbyUpdateEvent> = _nearbyUpdate.asSharedFlow()

    private val _tagMatchAlerts = MutableSharedFlow<List<TagMatchAlert>>(extraBufferCapacity = 8)
    val tagMatchAlerts: SharedFlow<List<TagMatchAlert>> = _tagMatchAlerts.asSharedFlow()

    data class State(
        val isAdvertising: Boolean = false,
        val isScanning: Boolean = false,
        val tempId: String? = null,
        val foundCount: Int = 0,
        val running: Boolean = false
    )

    data class NearbyUpdateEvent(
        val resolved: List<ResolvedDevice>,
        val boostDeviceIds: List<String>,
        val leftFriendIds: List<String> = emptyList()  // Friends who left the range
    )

    data class ResolvedDevice(
        val deviceId: String,
        val nickname: String,
        val avatar: String?,
        val tags: List<String>,
        val profile: String,
        val isAnonymous: Boolean,
        val roleName: String?,
        val isFriend: Boolean,
        val rssi: Int,
        val distanceEstimate: Float
    )

    // ---------- lifecycle ----------

    fun start(context: Context) {
        if (_state.value.running) return
        advertiser = BleAdvertiser(context)
        scanner = BleScanner(context)
        _state.update { it.copy(running = true) }

        startTempIdLoop()
        startScanLoop()
        startCollecting()
        Log.d(TAG, "BleManager started")
    }

    fun stop() {
        scanLoopJob?.cancel()
        tempIdJob?.cancel()
        collectJob?.cancel()
        advertiser?.stop()
        scanner?.stop()
        bleFindMap.clear()
        tagMatchSignatures.clear()
        nearbyFriendIds.clear()
        _state.value = State()
        Log.d(TAG, "BleManager stopped")
    }

    // ---------- 8.4 temp_id 管理 ----------

    private fun startTempIdLoop() {
        tempIdJob?.cancel()
        tempIdJob = scope.launch {
            while (isActive) {
                val data = TempIdRepository.refresh()
                if (data != null) {
                    _state.update { it.copy(tempId = data.tempId) }
                    advertiser?.start(data.tempId)
                    _state.update { it.copy(isAdvertising = advertiser?.isAdvertising() == true) }

                    val delayMs = calculateRefreshDelay(data.expiresAt)
                    Log.d(TAG, "Next temp_id refresh in ${delayMs / 1000}s")
                    delay(delayMs)
                } else {
                    delay(30_000)
                }
            }
        }
    }

    // ---------- 8.3 扫描循环 ----------

    private fun startScanLoop() {
        scanLoopJob?.cancel()
        scanLoopJob = scope.launch {
            while (isActive) {
                resetScanWindow()
                scanner?.start()
                _state.update { it.copy(isScanning = true) }

                delay(BleConstants.SCAN_DURATION_MS)

                scanner?.stop()
                _state.update { it.copy(isScanning = false) }

                resolveAndUpdate()

                delay(BleConstants.SCAN_INTERVAL_MS - BleConstants.SCAN_DURATION_MS)
            }
        }
    }

    private fun startCollecting() {
        collectJob?.cancel()
        collectJob = scope.launch {
            scanner?.found?.collect { device ->
                bleFindMap[device.tempId] = device
                _state.update { it.copy(foundCount = bleFindMap.size) }
            }
        }
    }

    // ---------- 8.5 上报 + 写库 ----------

    private suspend fun resolveAndUpdate() {
        val snapshot = synchronized(bleFindMap) { bleFindMap.values.toList() }
        if (snapshot.isEmpty()) {
            tagMatchSignatures.clear()
            val leftFriends = checkForLeftFriends(emptySet())
            _nearbyUpdate.tryEmit(NearbyUpdateEvent(emptyList(), emptyList(), leftFriends))
            Log.d(TAG, "Resolved 0 devices, 0 boosts, ${leftFriends.size} friends left")
            return
        }

        val scanned = snapshot.map { ScannedDevice(tempId = it.tempId, rssi = it.rssi) }
        val result = PresenceRepository.resolveNearby(scanned) ?: return

        val chatHistoryDao = NotePassingApp.instance.database.chatHistoryDao()
        val friendDao = NotePassingApp.instance.database.friendDao()
        val now = System.currentTimeMillis()
        
        // Track current nearby friend IDs for this scan
        val currentNearbyFriendIds = mutableSetOf<String>()
        val reunionAlerts = mutableListOf<FriendReunionAlert>()

        val resolved = result.nearbyDevices.map { dto ->
            val existing = chatHistoryDao.getByDeviceId(dto.deviceId)
            chatHistoryDao.insertOrReplace(
                ChatHistoryEntity(
                    deviceId = dto.deviceId,
                    nickname = dto.nickname,
                    avatar = dto.avatar,
                    tags = TagSerializer.encode(dto.tags),
                    profile = dto.profile,
                    isAnonymous = dto.isAnonymous,
                    roleName = dto.roleName,
                    isFriend = dto.isFriend,
                    sessionId = existing?.sessionId,
                    lastMessage = existing?.lastMessage,
                    lastMessageAt = existing?.lastMessageAt,
                    lastSeenAt = now,
                    firstSeenAt = existing?.firstSeenAt ?: now,
                    // Once a device is discovered again in the current scan window,
                    // its temporary session becomes active again and the card should reappear.
                    isSessionExpired = false,
                )
            )
            
            // Update friends table for nearby friends
            if (dto.isFriend) {
                currentNearbyFriendIds.add(dto.deviceId)
                if (updateFriendNearbyStatus(friendDao, dto.deviceId, now)) {
                    reunionAlerts += FriendReunionAlert(
                        deviceId = dto.deviceId,
                        nickname = dto.nickname,
                    )
                }
            }
            
            val rssi = snapshot.find { it.tempId == dto.tempId }?.rssi ?: -100
            ResolvedDevice(
                deviceId = dto.deviceId,
                nickname = dto.nickname,
                avatar = dto.avatar,
                tags = dto.tags,
                profile = dto.profile,
                isAnonymous = dto.isAnonymous,
                roleName = dto.roleName,
                isFriend = dto.isFriend,
                rssi = rssi,
                distanceEstimate = dto.distanceEstimate
            )
        }
        
        // Check for friends who left the range
        val leftFriends = checkForLeftFriends(currentNearbyFriendIds)
        if (leftFriends.isNotEmpty()) {
            // Update left friends' isNearby status to false
            leftFriends.forEach { friendId ->
                friendDao.updateNearbyStatus(friendId, false)
                Log.d(TAG, "Friend left range: $friendId")
            }
        }

        handleTagMatchAlerts(resolved)

        if (reunionAlerts.isNotEmpty()) {
            FriendReunionNotifier.notify(NotePassingApp.instance, reunionAlerts)
            Log.d(TAG, "Friend reunion alerts: ${reunionAlerts.size}")
        }

        val boostIds = result.boostAlerts.map { it.deviceId }
        _nearbyUpdate.tryEmit(NearbyUpdateEvent(resolved, boostIds, leftFriends))
        Log.d(TAG, "Resolved ${resolved.size} devices, ${boostIds.size} boosts, ${leftFriends.size} friends left")
    }

    private fun resetScanWindow() {
        synchronized(bleFindMap) {
            bleFindMap.clear()
        }
        _state.update { it.copy(foundCount = 0) }
    }
    
    /**
     * Update friend's nearby status and increment meet count if newly nearby
     */
    private suspend fun updateFriendNearbyStatus(friendDao: com.example.notepassingapp.data.local.dao.FriendDao, friendId: String, now: Long): Boolean {
        val wasNearby = nearbyFriendIds.contains(friendId)
        if (!wasNearby) {
            // Friend newly came into range - update isNearby and increment meetCount
            friendDao.updateNearbyStatus(friendId, true)
            friendDao.incrementMeetCount(friendId)
            nearbyFriendIds.add(friendId)
            Log.d(TAG, "Friend came into range: $friendId, meetCount incremented")
            return true
        }
        return false
    }
    
    /**
     * Check for friends who were nearby but are no longer in range
     */
    private fun checkForLeftFriends(currentNearbyIds: Set<String>): List<String> {
        synchronized(nearbyFriendIds) {
            val leftFriends = nearbyFriendIds.filter { it !in currentNearbyIds }
            nearbyFriendIds.removeAll(leftFriends.toSet())
            return leftFriends
        }
    }

    private fun handleTagMatchAlerts(resolved: List<ResolvedDevice>) {
        val myTags = DeviceManager.getTags()
        if (myTags.isEmpty()) {
            tagMatchSignatures.clear()
            return
        }

        val activeAlerts = resolved.mapNotNull { device ->
            val commonTags = TagSerializer.findCommonTags(myTags, device.tags)
            if (commonTags.isEmpty()) {
                null
            } else {
                TagMatchAlert(
                    deviceId = device.deviceId,
                    nickname = device.nickname,
                    commonTags = commonTags,
                )
            }
        }

        val activeSignatures = activeAlerts.associate { alert ->
            alert.deviceId to alert.commonTags.joinToString("|") { it.lowercase() }
        }

        synchronized(tagMatchSignatures) {
            val staleIds = tagMatchSignatures.keys.toSet() - activeSignatures.keys
            staleIds.forEach(tagMatchSignatures::remove)

            val newAlerts = activeAlerts.filter { alert ->
                alert.deviceId !in announcedTagMatchDeviceIds &&
                    tagMatchSignatures[alert.deviceId] != activeSignatures[alert.deviceId]
            }
            if (newAlerts.isEmpty()) return

            newAlerts.forEach { alert ->
                tagMatchSignatures[alert.deviceId] = activeSignatures.getValue(alert.deviceId)
                announcedTagMatchDeviceIds.add(alert.deviceId)
            }

            TagMatchNotifier.notify(NotePassingApp.instance, newAlerts)
            _tagMatchAlerts.tryEmit(newAlerts)
            Log.d(TAG, "Tag match alerts: ${newAlerts.size}")
        }
    }

    // ---------- util ----------

    private val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }

    private fun calculateRefreshDelay(expiresAt: String): Long {
        return try {
            val clean = expiresAt.substringBefore("Z").substringBefore("+")
                .let { if (it.contains(".")) it.substringBefore(".") else it }
            val expiry = sdf.parse(clean)!!.time
            val delay = expiry - System.currentTimeMillis() - 30_000
            maxOf(delay, 10_000L)
        } catch (e: Exception) {
            Log.w(TAG, "Cannot parse expiresAt=$expiresAt", e)
            300_000L
        }
    }
}
