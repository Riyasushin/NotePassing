package com.example.notepassingapp.ui.debug

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.notepassingapp.ble.BleManager
import com.example.notepassingapp.data.remote.ApiClient
import com.example.notepassingapp.data.remote.DebugLogInterceptor
import com.example.notepassingapp.data.remote.HttpLogEntry
import com.example.notepassingapp.data.remote.NetworkConfig
import com.example.notepassingapp.data.remote.ws.WebSocketManager
import com.example.notepassingapp.data.repository.*
import com.example.notepassingapp.util.DeviceManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
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

    private val _httpLogs = MutableStateFlow<List<HttpLogEntry>>(emptyList())
    val httpLogs: StateFlow<List<HttpLogEntry>> = _httpLogs.asStateFlow()

    private val _wsState = MutableStateFlow("未知")
    val wsState: StateFlow<String> = _wsState.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _selectedTab = MutableStateFlow(0)
    val selectedTab: StateFlow<Int> = _selectedTab.asStateFlow()

    val bleState = BleManager.state

    private val timeFormat = SimpleDateFormat("HH:mm:ss.SSS", Locale.getDefault())

    init {
        addLog("系统", "Debug 面板启动")
        addLog("配置", "REST: ${NetworkConfig.BASE_URL}")
        addLog("配置", "WS:   ${NetworkConfig.WS_URL}")
        addLog("设备", "device_id: ${DeviceManager.getDeviceId()}")
        addLog("设备", "nickname: ${DeviceManager.getNickname()}")

        addLog("WS状态", "当前: ${if (WebSocketManager.isConnected()) "已连接" else "未连接"}")

        observeWsState()
        observeWsMessages()
        observeWsRaw()
        observeHttpLogs()
        observeBleState()
    }

    fun selectTab(index: Int) { _selectedTab.value = index }

    private fun observeWsState() {
        viewModelScope.launch {
            WebSocketManager.connectionState.collect { state ->
                _wsState.value = state.name
                addLog("WS状态", "→ $state")
            }
        }
    }

    private fun observeWsMessages() {
        viewModelScope.launch {
            WebSocketManager.incomingMessages.collect { msg ->
                val payloadStr = msg.payload?.toString()?.take(500) ?: "(null)"
                addLog("WS解析", "[${msg.type}] $payloadStr")
            }
        }
    }

    private fun observeWsRaw() {
        viewModelScope.launch {
            WebSocketManager.rawMessages.collect { raw ->
                if (!raw.contains("\"type\":\"pong\"") && !raw.contains("\"type\": \"pong\"")) {
                    addLog("WS原始", raw.take(500))
                }
            }
        }
    }

    private fun observeHttpLogs() {
        viewModelScope.launch {
            DebugLogInterceptor.logs.collect {
                _httpLogs.value = DebugLogInterceptor.logList.reversed()
            }
        }
    }

    private fun observeBleState() {
        viewModelScope.launch {
            BleManager.state.collect { s ->
                if (s.running) {
                    addLog("BLE", "advertising=${s.isAdvertising} scanning=${s.isScanning} found=${s.foundCount} tempId=${s.tempId?.take(8) ?: "null"}")
                }
            }
        }
    }

    fun testDeviceInit() {
        runApiTest("device/init") { DeviceRepository.initDevice() }
    }

    fun testSyncProfile() {
        runApiTest("PUT /device/{id}") { DeviceRepository.syncProfile() }
    }

    fun testRefreshTempId() {
        runApiTest("temp-id/refresh") {
            val data = TempIdRepository.refresh()
            if (data != null) {
                "成功 ✓ temp_id=${data.tempId.take(16)}... expires=${data.expiresAt}"
            } else {
                "失败 ✗（可能需要先 device/init）"
            }
        }
    }

    fun testSyncFriends() {
        runApiTest("GET /friends") {
            try {
                val response = ApiClient.relationApi
                    .getFriendsList(DeviceManager.getDeviceId())
                if (response.isSuccess) {
                    "成功 ✓ 好友数: ${response.data?.friends?.size ?: 0}"
                } else {
                    "服务器拒绝: code=${response.code} msg=${response.message}"
                }
            } catch (e: Exception) {
                "异常: ${e.javaClass.simpleName}: ${e.message}"
            }
        }
    }

    fun testServerPing() {
        runApiTest("服务器连通性") {
            withContext(Dispatchers.IO) {
                val url = NetworkConfig.BASE_URL.removeSuffix("api/v1/").removeSuffix("/")
                val request = okhttp3.Request.Builder().url(url).build()
                val response = ApiClient.okHttpClient.newCall(request).execute()
                val body = response.body?.string()?.take(200) ?: "(empty)"
                "HTTP ${response.code} → $body"
            }
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
        DebugLogInterceptor.clear()
        _httpLogs.value = emptyList()
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
