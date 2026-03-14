package com.example.notepassingapp.data.repository

import android.util.Log
import com.example.notepassingapp.data.remote.ApiClient
import com.example.notepassingapp.data.remote.dto.*
import com.example.notepassingapp.util.DeviceManager

object PresenceRepository {

    private const val TAG = "PresenceRepository"

    /**
     * BLE 扫描到 temp_id 列表后，调用服务器解析为用户信息。
     */
    suspend fun resolveNearby(
        scannedDevices: List<ScannedDevice>
    ): PresenceResolveData? {
        if (scannedDevices.isEmpty()) return null

        return try {
            val request = PresenceResolveRequest(
                deviceId = DeviceManager.getDeviceId(),
                scannedDevices = scannedDevices
            )
            val response = ApiClient.presenceApi.resolveNearby(request)
            if (response.isSuccess) {
                response.data
            } else {
                Log.w(TAG, "Resolve failed: ${response.code} ${response.message}")
                null
            }
        } catch (e: Exception) {
            Log.e(TAG, "Resolve error", e)
            null
        }
    }

    /**
     * 某设备 ~1 分钟未被扫描到时，上报离开。
     */
    suspend fun reportDisconnect(leftDeviceId: String): PresenceDisconnectData? {
        return try {
            val request = PresenceDisconnectRequest(
                deviceId = DeviceManager.getDeviceId(),
                leftDeviceId = leftDeviceId
            )
            val response = ApiClient.presenceApi.reportDisconnect(request)
            response.data
        } catch (e: Exception) {
            Log.e(TAG, "Disconnect report error", e)
            null
        }
    }
}
