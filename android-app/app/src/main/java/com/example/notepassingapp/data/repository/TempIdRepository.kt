package com.example.notepassingapp.data.repository

import android.util.Log
import com.example.notepassingapp.data.remote.ApiClient
import com.example.notepassingapp.data.remote.dto.TempIdData
import com.example.notepassingapp.data.remote.dto.TempIdRefreshRequest
import com.example.notepassingapp.util.DeviceManager

object TempIdRepository {

    private const val TAG = "TempIdRepository"

    var currentTempId: String? = null
        private set
    var expiresAt: String? = null
        private set

    /**
     * 向服务器请求新的 temp_id，用于 BLE 广播。
     */
    suspend fun refresh(): TempIdData? {
        return try {
            val request = TempIdRefreshRequest(
                deviceId = DeviceManager.getDeviceId(),
                currentTempId = currentTempId
            )
            val response = ApiClient.tempIdApi.refreshTempId(request)
            if (response.isSuccess && response.data != null) {
                currentTempId = response.data.tempId
                expiresAt = response.data.expiresAt
                Log.d(TAG, "TempId refreshed: ${currentTempId?.take(8)}...")
                response.data
            } else {
                Log.w(TAG, "TempId refresh failed: ${response.code}")
                null
            }
        } catch (e: Exception) {
            Log.e(TAG, "TempId refresh error", e)
            null
        }
    }
}
