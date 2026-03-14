package com.example.notepassingapp.ble

import android.content.Context
import android.util.Log
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.local.entity.ChatHistoryEntity
import com.example.notepassingapp.data.remote.dto.ScannedDevice
import com.example.notepassingapp.data.repository.PresenceRepository
import com.example.notepassingapp.data.repository.TempIdRepository
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

    // ---------- exposed state ----------

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    private val _nearbyUpdate = MutableSharedFlow<NearbyUpdateEvent>(extraBufferCapacity = 8)
    val nearbyUpdate: SharedFlow<NearbyUpdateEvent> = _nearbyUpdate.asSharedFlow()

    data class State(
        val isAdvertising: Boolean = false,
        val isScanning: Boolean = false,
        val tempId: String? = null,
        val foundCount: Int = 0,
        val running: Boolean = false
    )

    data class NearbyUpdateEvent(
        val resolved: List<ResolvedDevice>,
        val boostDeviceIds: List<String>
    )

    data class ResolvedDevice(
        val deviceId: String,
        val nickname: String,
        val avatar: String?,
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
                scanner?.start()
                _state.update { it.copy(isScanning = true) }

                delay(BleConstants.SCAN_DURATION_MS)

                scanner?.stop()
                _state.update { it.copy(isScanning = false) }

                resolveAndUpdate()
                cleanStale()

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
        if (snapshot.isEmpty()) return

        val scanned = snapshot.map { ScannedDevice(tempId = it.tempId, rssi = it.rssi) }
        val result = PresenceRepository.resolveNearby(scanned) ?: return

        val dao = NotePassingApp.instance.database.chatHistoryDao()
        val now = System.currentTimeMillis()

        val resolved = result.nearbyDevices.map { dto ->
            val existing = dao.getByDeviceId(dto.deviceId)
            dao.insertOrReplace(
                ChatHistoryEntity(
                    deviceId = dto.deviceId,
                    nickname = dto.nickname,
                    avatar = dto.avatar,
                    profile = dto.profile,
                    isAnonymous = dto.isAnonymous,
                    roleName = dto.roleName,
                    isFriend = dto.isFriend,
                    lastSeenAt = now,
                    firstSeenAt = existing?.firstSeenAt ?: now
                )
            )
            val rssi = snapshot.find { it.tempId == dto.tempId }?.rssi ?: -100
            ResolvedDevice(
                deviceId = dto.deviceId,
                nickname = dto.nickname,
                avatar = dto.avatar,
                profile = dto.profile,
                isAnonymous = dto.isAnonymous,
                roleName = dto.roleName,
                isFriend = dto.isFriend,
                rssi = rssi,
                distanceEstimate = dto.distanceEstimate
            )
        }

        val boostIds = result.boostAlerts.map { it.deviceId }
        _nearbyUpdate.tryEmit(NearbyUpdateEvent(resolved, boostIds))
        Log.d(TAG, "Resolved ${resolved.size} devices, ${boostIds.size} boosts")
    }

    private fun cleanStale() {
        val cutoff = System.currentTimeMillis() - BleConstants.STALE_CLEANUP_MS
        synchronized(bleFindMap) {
            bleFindMap.entries.removeAll { it.value.timestamp < cutoff }
        }
        _state.update { it.copy(foundCount = bleFindMap.size) }
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
