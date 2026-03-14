package com.example.notepassingapp.ui.debug

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.notepassingapp.data.remote.NetworkConfig
import com.example.notepassingapp.data.remote.ws.WebSocketManager
import com.example.notepassingapp.data.repository.*
import com.example.notepassingapp.util.DeviceManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

data class LogEntry(
    val time: String,
    val tag: String,
    val message: String,
    val isError: Boolean = false
)

class DebugViewModel : ViewModel() {

    private val _logs = MutableStateFlow<List<LogEntry>>(emptyList())
    val logs: StateFlow<List<LogEntry>> = _logs.asStateFlow()

    private val _wsState = MutableStateFlow("未知")
    val wsState: StateFlow<String> = _wsState.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val timeFormat = SimpleDateFormat("HH:mm:ss.SSS", Locale.getDefault())

    init {
        addLog("系统", "Debug 面板启动")
        addLog("配置", "REST: ${NetworkConfig.BASE_URL}")
        addLog("配置", "WS:   ${NetworkConfig.WS_URL}")
        addLog("设备", "device_id: ${DeviceManager.getDeviceId()}")
        addLog("设备", "nickname: ${DeviceManager.getNickname()}")

        observeWsState()
    }

    private fun observeWsState() {
        viewModelScope.launch {
            WebSocketManager.connectionState.collect { state ->
                _wsState.value = state.name
                addLog("WebSocket", "状态变更 → $state")
            }
        }
    }

    fun testDeviceInit() {
        runApiTest("device/init") {
            val ok = DeviceRepository.initDevice()
            if (ok) "成功 ✓" else "失败 ✗"
        }
    }

    fun testSyncProfile() {
        runApiTest("PUT /device/{id}") {
            val ok = DeviceRepository.syncProfile()
            if (ok) "同步成功 ✓" else "同步失败 ✗"
        }
    }

    fun testRefreshTempId() {
        runApiTest("temp-id/refresh") {
            val data = TempIdRepository.refresh()
            if (data != null) {
                "成功 ✓\ntemp_id: ${data.tempId.take(16)}...\nexpires_at: ${data.expiresAt}"
            } else {
                "失败 ✗"
            }
        }
    }

    fun testSyncFriends() {
        runApiTest("GET /friends") {
            val ok = RelationRepository.syncFriends()
            if (ok) "同步成功 ✓" else "同步失败 ✗"
        }
    }

    fun testWsConnect() {
        addLog("WebSocket", "手动发起连接...")
        WebSocketManager.connect()
    }

    fun testWsDisconnect() {
        addLog("WebSocket", "手动断开...")
        WebSocketManager.disconnect()
    }

    fun testWsPing() {
        if (WebSocketManager.isConnected()) {
            WebSocketManager.sendChatMessage(
                receiverId = "test-ping",
                content = "ping-test",
                type = "heartbeat"
            )
            addLog("WebSocket", "已发送测试 heartbeat")
        } else {
            addLog("WebSocket", "未连接，无法发送", isError = true)
        }
    }

    fun clearLogs() {
        _logs.value = emptyList()
        addLog("系统", "日志已清除")
    }

    private fun runApiTest(name: String, block: suspend () -> String) {
        viewModelScope.launch {
            _isLoading.value = true
            addLog("请求", "→ $name")
            try {
                val result = block()
                addLog("响应", "← $name: $result")
            } catch (e: Exception) {
                addLog("错误", "← $name: ${e.javaClass.simpleName}: ${e.message}", isError = true)
            }
            _isLoading.value = false
        }
    }

    private fun addLog(tag: String, message: String, isError: Boolean = false) {
        val entry = LogEntry(
            time = timeFormat.format(Date()),
            tag = tag,
            message = message,
            isError = isError
        )
        _logs.value = _logs.value + entry
    }
}
