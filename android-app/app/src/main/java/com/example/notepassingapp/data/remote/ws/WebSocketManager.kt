package com.example.notepassingapp.data.remote.ws

import android.util.Log
import com.example.notepassingapp.data.remote.ApiClient
import com.example.notepassingapp.data.remote.NetworkConfig
import com.example.notepassingapp.util.DeviceManager
import com.google.gson.Gson
import com.google.gson.JsonObject
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import okhttp3.*

/**
 * WebSocket 管理器：单连接、自动重连、ping 保活、消息分发。
 *
 * 使用方式：
 *   WebSocketManager.connect()          // App 启动后调用
 *   WebSocketManager.incomingMessages    // 订阅服务端推送
 *   WebSocketManager.sendMessage(...)    // 发送消息
 */
object WebSocketManager {

    private const val TAG = "WebSocketManager"
    private val gson = Gson()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private var webSocket: WebSocket? = null
    private var isConnected = false
    private var reconnectAttempt = 0
    private var pingJob: Job? = null
    private var shouldConnect = false

    private val _incomingMessages = MutableSharedFlow<WsServerMessage>(extraBufferCapacity = 64)
    val incomingMessages: SharedFlow<WsServerMessage> = _incomingMessages.asSharedFlow()

    private val _rawMessages = MutableSharedFlow<String>(extraBufferCapacity = 64)
    val rawMessages: SharedFlow<String> = _rawMessages.asSharedFlow()

    private val _connectionState = MutableSharedFlow<ConnectionState>(replay = 1, extraBufferCapacity = 4)
    val connectionState: SharedFlow<ConnectionState> = _connectionState.asSharedFlow()

    enum class ConnectionState { CONNECTING, CONNECTED, DISCONNECTED, RECONNECTING }

    fun connect() {
        shouldConnect = true
        reconnectAttempt = 0
        doConnect()
    }

    fun disconnect() {
        shouldConnect = false
        pingJob?.cancel()
        webSocket?.close(1000, "Client disconnect")
        webSocket = null
        isConnected = false
        _connectionState.tryEmit(ConnectionState.DISCONNECTED)
    }

    private fun doConnect() {
        if (!shouldConnect) return

        val deviceId = DeviceManager.getDeviceId()
        val url = "${NetworkConfig.WS_URL}?device_id=$deviceId"
        val request = Request.Builder().url(url).build()

        _connectionState.tryEmit(
            if (reconnectAttempt == 0) ConnectionState.CONNECTING else ConnectionState.RECONNECTING
        )
        Log.d(TAG, "Connecting to WS: $url (attempt #$reconnectAttempt)")

        webSocket = ApiClient.okHttpClient.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d(TAG, "WS connected")
                isConnected = true
                reconnectAttempt = 0
                _connectionState.tryEmit(ConnectionState.CONNECTED)
                startPing()
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                Log.d(TAG, "WS raw: $text")
                _rawMessages.tryEmit(text)
                try {
                    val msg = gson.fromJson(text, WsServerMessage::class.java)
                    if (msg.type == WsTypes.PONG) return
                    _incomingMessages.tryEmit(msg)
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to parse WS message: $text", e)
                }
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                Log.d(TAG, "WS closing: $code $reason")
                webSocket.close(code, reason)
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.d(TAG, "WS closed: $code $reason")
                handleDisconnect()
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "WS failure: ${t.message}")
                handleDisconnect()
            }
        })
    }

    private fun handleDisconnect() {
        isConnected = false
        pingJob?.cancel()
        _connectionState.tryEmit(ConnectionState.DISCONNECTED)

        if (shouldConnect) {
            scheduleReconnect()
        }
    }

    private fun scheduleReconnect() {
        reconnectAttempt++
        val delayMs = minOf(reconnectAttempt * 2000L, 30000L)
        Log.d(TAG, "Reconnecting in ${delayMs}ms (attempt #$reconnectAttempt)")

        scope.launch {
            delay(delayMs)
            if (shouldConnect && !isConnected) {
                doConnect()
            }
        }
    }

    private fun startPing() {
        pingJob?.cancel()
        pingJob = scope.launch {
            while (isActive && isConnected) {
                delay(NetworkConfig.WS_PING_INTERVAL_SEC * 1000)
                send(WsActions.PING, null)
            }
        }
    }

    // ===== 发送方法 =====

    fun sendChatMessage(receiverId: String, content: String, type: String = "common") {
        val payload = gson.toJsonTree(
            WsSendMessagePayload(receiverId, content, type)
        ).asJsonObject
        send(WsActions.SEND_MESSAGE, payload)
    }

    fun sendMarkRead(messageIds: List<String>) {
        val payload = gson.toJsonTree(
            WsMarkReadPayload(messageIds)
        ).asJsonObject
        send(WsActions.MARK_READ, payload)
    }

    private fun send(action: String, payload: JsonObject?) {
        val msg = WsClientMessage(action, payload)
        val json = gson.toJson(msg)
        val sent = webSocket?.send(json) ?: false
        if (!sent) {
            Log.w(TAG, "WS send failed (not connected): $action")
        }
    }

    fun isConnected(): Boolean = isConnected
}
