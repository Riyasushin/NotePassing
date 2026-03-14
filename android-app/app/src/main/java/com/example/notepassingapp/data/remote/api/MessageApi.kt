package com.example.notepassingapp.data.remote.api

import com.example.notepassingapp.data.remote.dto.*
import retrofit2.http.*

/**
 * 契约 §4 Messaging Service
 */
interface MessageApi {

    @POST("messages")
    suspend fun sendMessage(
        @Body request: SendMessageRequest
    ): ApiResponse<SendMessageData>

    @GET("messages/{session_id}")
    suspend fun getHistory(
        @Path("session_id") sessionId: String,
        @Query("device_id") deviceId: String,
        @Query("before") before: String? = null,
        @Query("after") after: String? = null,
        @Query("limit") limit: Int? = null
    ): ApiResponse<MessageHistoryData>

    @POST("messages/read")
    suspend fun markRead(
        @Body request: MarkReadRequest
    ): ApiResponse<MarkReadData>

    @GET("messages/sync")
    suspend fun syncMessages(
        @Query("device_id") deviceId: String,
        @Query("after") after: String,
        @Query("limit") limit: Int? = null
    ): ApiResponse<SyncMessagesData>
}
