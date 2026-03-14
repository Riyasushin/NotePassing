package com.example.notepassingapp.data.remote.dto

import com.google.gson.annotations.SerializedName

// ===== §3.1 解析附近设备 =====

data class PresenceResolveRequest(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("scanned_devices") val scannedDevices: List<ScannedDevice>
)

data class ScannedDevice(
    @SerializedName("temp_id") val tempId: String,
    @SerializedName("rssi") val rssi: Int
)

data class PresenceResolveData(
    @SerializedName("nearby_devices") val nearbyDevices: List<NearbyDeviceDto>,
    @SerializedName("boost_alerts") val boostAlerts: List<BoostAlertDto>
)

data class NearbyDeviceDto(
    @SerializedName("temp_id") val tempId: String,
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("nickname") val nickname: String,
    @SerializedName("avatar") val avatar: String?,
    @SerializedName("tags") val tags: List<String>,
    @SerializedName("profile") val profile: String,
    @SerializedName("is_anonymous") val isAnonymous: Boolean,
    @SerializedName("role_name") val roleName: String?,
    @SerializedName("distance_estimate") val distanceEstimate: Float,
    @SerializedName("is_friend") val isFriend: Boolean
)

data class BoostAlertDto(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("nickname") val nickname: String,
    @SerializedName("distance_estimate") val distanceEstimate: Float
)

// ===== §3.2 上报离开范围 =====

data class PresenceDisconnectRequest(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("left_device_id") val leftDeviceId: String
)

data class PresenceDisconnectData(
    @SerializedName("session_expired") val sessionExpired: Boolean,
    @SerializedName("session_id") val sessionId: String?
)
