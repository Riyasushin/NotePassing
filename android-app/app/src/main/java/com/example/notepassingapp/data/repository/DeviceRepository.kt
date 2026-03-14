package com.example.notepassingapp.data.repository

import android.util.Log
import com.example.notepassingapp.data.remote.ApiClient
import com.example.notepassingapp.data.remote.dto.*
import com.example.notepassingapp.util.DeviceManager

object DeviceRepository {

    private const val TAG = "DeviceRepository"

    /**
     * 启动时调用：向服务器注册/恢复设备。
     * 成功返回 true，失败返回 false（不影响本地使用）。
     */
    suspend fun initDevice(): Boolean {
        return try {
            val request = DeviceInitRequest(
                deviceId = DeviceManager.getDeviceId(),
                nickname = DeviceManager.getNickname(),
                profile = DeviceManager.getProfile()
            )
            val response = ApiClient.deviceApi.initDevice(request)
            if (response.isSuccess) {
                Log.d(TAG, "Device init success, is_new=${response.data?.isNew}")
                true
            } else {
                Log.w(TAG, "Device init failed: ${response.code} ${response.message}")
                false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Device init error", e)
            false
        }
    }

    /**
     * 更新设备资料到服务器（设置页保存时调用）。
     */
    suspend fun syncProfile(): Boolean {
        return try {
            val request = DeviceUpdateRequest(
                nickname = DeviceManager.getNickname(),
                avatar = DeviceManager.getAvatar(),
                profile = DeviceManager.getProfile(),
                isAnonymous = DeviceManager.isAnonymous(),
                roleName = DeviceManager.getRoleName()
            )
            val response = ApiClient.deviceApi.updateProfile(
                DeviceManager.getDeviceId(), request
            )
            if (response.isSuccess) {
                Log.d(TAG, "Profile synced to server")
                true
            } else {
                Log.w(TAG, "Profile sync failed: ${response.code} ${response.message}")
                false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Profile sync error", e)
            false
        }
    }

    /**
     * 获取对方的资料（用于聊天页展示对方信息）。
     */
    suspend fun getProfile(targetDeviceId: String): DeviceProfileData? {
        return try {
            val response = ApiClient.deviceApi.getProfile(
                targetDeviceId, DeviceManager.getDeviceId()
            )
            response.data
        } catch (e: Exception) {
            Log.e(TAG, "Get profile error", e)
            null
        }
    }
}
