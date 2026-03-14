package com.example.notepassingapp.data.remote.api

import com.example.notepassingapp.data.remote.dto.*
import retrofit2.http.Body
import retrofit2.http.POST

/**
 * 契约 §3 Presence Service
 */
interface PresenceApi {

    @POST("presence/resolve")
    suspend fun resolveNearby(
        @Body request: PresenceResolveRequest
    ): ApiResponse<PresenceResolveData>

    @POST("presence/disconnect")
    suspend fun reportDisconnect(
        @Body request: PresenceDisconnectRequest
    ): ApiResponse<PresenceDisconnectData>
}
