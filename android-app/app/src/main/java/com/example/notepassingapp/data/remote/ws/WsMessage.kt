package com.example.notepassingapp.data.remote.ws

import com.google.gson.JsonObject
import com.google.gson.annotations.SerializedName

// ===== 客户端 → 服务器（契约 §6.2）=====

data class WsClientMessage(
    @SerializedName("action") val action: String,
    @SerializedName("payload") val payload: JsonObject? = null
)

object WsActions {
    const val SEND_MESSAGE = "send_message"
    const val MARK_READ = "mark_read"
    const val PING = "ping"
}

// ===== 服务器 → 客户端（契约 §6.3）=====

data class WsServerMessage(
    @SerializedName("type") val type: String,
    @SerializedName("payload") val payload: JsonObject? = null
)

object WsTypes {
    const val CONNECTED = "connected"
    const val NEW_MESSAGE = "new_message"
    const val MESSAGE_SENT = "message_sent"
    const val FRIEND_REQUEST = "friend_request"
    const val FRIEND_RESPONSE = "friend_response"
    const val BOOST = "boost"
    const val SESSION_EXPIRED = "session_expired"
    const val MESSAGES_READ = "messages_read"
    const val PONG = "pong"
    const val ERROR = "error"
}
