package com.example.notepassingapp.data.remote

import com.example.notepassingapp.BuildConfig

object NetworkConfig {
    private const val REST_SCHEME = "http"
    private const val WS_SCHEME = "ws"
    private const val API_PREFIX = "/api/v1"

    val SERVER_HOST: String = BuildConfig.SERVER_HOST
    val BASE_URL: String = "$REST_SCHEME://$SERVER_HOST$API_PREFIX/"
    val WS_URL: String = "$WS_SCHEME://$SERVER_HOST$API_PREFIX/ws"

    const val CONNECT_TIMEOUT_SEC = 10L
    const val READ_TIMEOUT_SEC = 30L
    const val WRITE_TIMEOUT_SEC = 15L

    const val WS_PING_INTERVAL_SEC = 30L
}
