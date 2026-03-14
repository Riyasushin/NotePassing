package com.example.notepassingapp.data.remote.dto

import com.google.gson.annotations.SerializedName

/**
 * 统一响应格式（契约 §0.3）
 * 成功: code=0, data=T
 * 失败: code=4001~5002, data=null
 */
data class ApiResponse<T>(
    @SerializedName("code") val code: Int,
    @SerializedName("message") val message: String,
    @SerializedName("data") val data: T?
) {
    val isSuccess: Boolean get() = code == 0
}
