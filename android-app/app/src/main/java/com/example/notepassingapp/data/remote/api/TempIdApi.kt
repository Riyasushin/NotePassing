package com.example.notepassingapp.data.remote.api

import com.example.notepassingapp.data.remote.dto.*
import retrofit2.http.Body
import retrofit2.http.POST

/**
 * 契约 §2 Temp ID Service
 */
interface TempIdApi {

    @POST("temp-id/refresh")
    suspend fun refreshTempId(
        @Body request: TempIdRefreshRequest
    ): ApiResponse<TempIdData>
}
