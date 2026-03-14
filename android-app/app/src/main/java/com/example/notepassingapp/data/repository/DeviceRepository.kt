package com.example.notepassingapp.data.repository

import android.net.Uri
import android.provider.OpenableColumns
import android.util.Log
import android.webkit.MimeTypeMap
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.remote.ApiClient
import com.example.notepassingapp.data.remote.dto.*
import com.example.notepassingapp.util.DeviceManager
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

object DeviceRepository {

    private const val TAG = "DeviceRepository"

    /**
     * 启动时调用：向服务器注册/恢复设备。
     * 返回详细结果字符串（Debug 面板用）。
     */
    suspend fun initDevice(): String {
        return try {
            val did = DeviceManager.getDeviceId()
            val nick = DeviceManager.getNickname()
            Log.d(TAG, "initDevice: id=${did.take(8)}... nick=$nick")

            val request = DeviceInitRequest(
                deviceId = did,
                nickname = nick.ifBlank { "用户${did.take(6)}" },
                profile = DeviceManager.getProfile()
            )
            val response = ApiClient.deviceApi.initDevice(request)
            if (response.isSuccess) {
                Log.d(TAG, "Device init success, is_new=${response.data?.isNew}")
                "成功 ✓ is_new=${response.data?.isNew}"
            } else {
                Log.w(TAG, "Device init failed: ${response.code} ${response.message}")
                "服务器拒绝: code=${response.code} msg=${response.message}"
            }
        } catch (e: Exception) {
            Log.e(TAG, "Device init error", e)
            "异常: ${e.javaClass.simpleName}: ${e.message}"
        }
    }

    /**
     * 更新设备资料到服务器。
     */
    suspend fun syncProfile(): String {
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
                "同步成功 ✓"
            } else {
                Log.w(TAG, "Profile sync failed: ${response.code} ${response.message}")
                "服务器拒绝: code=${response.code} msg=${response.message}"
            }
        } catch (e: Exception) {
            Log.e(TAG, "Profile sync error", e)
            "异常: ${e.javaClass.simpleName}: ${e.message}"
        }
    }

    suspend fun uploadAvatar(uri: Uri): Result<String> {
        return try {
            val contentResolver = NotePassingApp.instance.contentResolver
            val mimeType = contentResolver.getType(uri) ?: "image/jpeg"
            val bytes = contentResolver.openInputStream(uri)?.use { it.readBytes() }
                ?: return Result.failure(Exception("无法读取所选图片"))

            val extension = MimeTypeMap.getSingleton()
                .getExtensionFromMimeType(mimeType)
                ?.takeIf { it.isNotBlank() }
                ?: "jpg"
            val fileName = queryDisplayName(uri) ?: "avatar.$extension"

            val requestBody = bytes.toRequestBody(mimeType.toMediaTypeOrNull())
            val filePart = MultipartBody.Part.createFormData("file", fileName, requestBody)

            val response = ApiClient.deviceApi.uploadAvatar(
                DeviceManager.getDeviceId(),
                filePart,
            )

            if (response.isSuccess && response.data != null) {
                DeviceManager.setAvatar(response.data.avatarUrl)
                Log.d(TAG, "Avatar uploaded: ${response.data.avatarUrl}")
                Result.success(response.data.avatarUrl)
            } else {
                Log.w(TAG, "Avatar upload failed: ${response.code} ${response.message}")
                Result.failure(Exception("${response.code}: ${response.message}"))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Avatar upload error", e)
            Result.failure(e)
        }
    }

    fun isInitSuccess(result: String) = result.contains("✓")

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

    private fun queryDisplayName(uri: Uri): String? {
        val contentResolver = NotePassingApp.instance.contentResolver
        return contentResolver.query(
            uri,
            arrayOf(OpenableColumns.DISPLAY_NAME),
            null,
            null,
            null,
        )?.use { cursor ->
            val columnIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (columnIndex >= 0 && cursor.moveToFirst()) {
                cursor.getString(columnIndex)
            } else {
                null
            }
        }
    }
}
