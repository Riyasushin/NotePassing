package com.example.notepassingapp.data.remote.dto

import com.google.gson.annotations.SerializedName

// ===== §2.1 刷新临时 ID =====

data class TempIdRefreshRequest(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("current_temp_id") val currentTempId: String? = null
)

data class TempIdData(
    @SerializedName("temp_id") val tempId: String,
    @SerializedName("expires_at") val expiresAt: String
)
