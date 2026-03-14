package com.example.notepassingapp.data.remote

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import okhttp3.Interceptor
import okhttp3.Response
import okio.Buffer
import java.nio.charset.Charset

data class HttpLogEntry(
    val timestamp: Long = System.currentTimeMillis(),
    val method: String,
    val url: String,
    val requestBody: String?,
    val responseCode: Int,
    val responseBody: String?,
    val durationMs: Long
)

object DebugLogInterceptor : Interceptor {

    private val _logs = MutableSharedFlow<HttpLogEntry>(extraBufferCapacity = 64)
    val logs: SharedFlow<HttpLogEntry> = _logs.asSharedFlow()

    private val _logList = mutableListOf<HttpLogEntry>()
    val logList: List<HttpLogEntry> get() = _logList.toList()

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val startMs = System.currentTimeMillis()

        val reqBody = request.body?.let {
            val buffer = Buffer()
            it.writeTo(buffer)
            buffer.readString(Charset.forName("UTF-8"))
        }

        val response = chain.proceed(request)
        val durationMs = System.currentTimeMillis() - startMs

        val respBody = response.body?.let {
            val source = it.source()
            source.request(Long.MAX_VALUE)
            source.buffer.clone().readString(Charset.forName("UTF-8"))
        }

        val entry = HttpLogEntry(
            method = request.method,
            url = request.url.toString(),
            requestBody = reqBody,
            responseCode = response.code,
            responseBody = respBody,
            durationMs = durationMs
        )

        synchronized(_logList) {
            _logList.add(entry)
            if (_logList.size > 100) _logList.removeAt(0)
        }
        _logs.tryEmit(entry)

        return response
    }

    fun clear() {
        synchronized(_logList) { _logList.clear() }
    }
}
