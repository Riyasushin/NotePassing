package com.example.notepassingapp.data.remote

object NetworkConfig {
    const val BASE_URL = "http://192.168.8.8:8000/api/v1/"
    const val WS_URL = "ws://192.168.8.8:8000/api/v1/ws"

    const val CONNECT_TIMEOUT_SEC = 10L
    const val READ_TIMEOUT_SEC = 30L
    const val WRITE_TIMEOUT_SEC = 15L

    const val WS_PING_INTERVAL_SEC = 30L
}
