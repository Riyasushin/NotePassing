package com.example.notepassingapp.data.remote.api

import com.example.notepassingapp.data.remote.dto.*
import retrofit2.http.*

/**
 * 契约 §1 Device Service
 */
interface DeviceApi {

    @POST("device/init")
    suspend fun initDevice(
        @Body request: DeviceInitRequest
    ): ApiResponse<DeviceInitData>

    @GET("device/{device_id}")
    suspend fun getProfile(
        @Path("device_id") deviceId: String,
        @Query("requester_id") requesterId: String
    ): ApiResponse<DeviceProfileData>

    @PUT("device/{device_id}")
    suspend fun updateProfile(
        @Path("device_id") deviceId: String,
        @Body request: DeviceUpdateRequest
    ): ApiResponse<DeviceUpdateData>
}
