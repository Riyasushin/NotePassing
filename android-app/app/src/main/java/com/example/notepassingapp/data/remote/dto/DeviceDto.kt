package com.example.notepassingapp.data.remote.dto

import com.google.gson.annotations.SerializedName

// ===== §1.1 设备初始化 =====

data class DeviceInitRequest(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("nickname") val nickname: String,
    @SerializedName("tags") val tags: List<String> = emptyList(),
    @SerializedName("profile") val profile: String = ""
)

data class DeviceInitData(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("nickname") val nickname: String,
    @SerializedName("is_new") val isNew: Boolean,
    @SerializedName("created_at") val createdAt: String
)

// ===== §1.2 获取设备资料 =====

data class DeviceProfileData(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("nickname") val nickname: String,
    @SerializedName("avatar") val avatar: String?,
    @SerializedName("tags") val tags: List<String>,
    @SerializedName("profile") val profile: String,
    @SerializedName("is_anonymous") val isAnonymous: Boolean,
    @SerializedName("role_name") val roleName: String?,
    @SerializedName("is_friend") val isFriend: Boolean
)

// ===== §1.3 更新设备资料 =====

data class DeviceUpdateRequest(
    @SerializedName("nickname") val nickname: String? = null,
    @SerializedName("avatar") val avatar: String? = null,
    @SerializedName("tags") val tags: List<String>? = null,
    @SerializedName("profile") val profile: String? = null,
    @SerializedName("is_anonymous") val isAnonymous: Boolean? = null,
    @SerializedName("role_name") val roleName: String? = null
)

data class DeviceUpdateData(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("nickname") val nickname: String,
    @SerializedName("avatar") val avatar: String?,
    @SerializedName("tags") val tags: List<String>,
    @SerializedName("profile") val profile: String,
    @SerializedName("is_anonymous") val isAnonymous: Boolean,
    @SerializedName("role_name") val roleName: String?,
    @SerializedName("updated_at") val updatedAt: String
)

data class AvatarUploadData(
    @SerializedName("avatar_url") val avatarUrl: String,
    @SerializedName("updated_at") val updatedAt: String
)
