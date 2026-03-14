package com.example.notepassingapp.util

import android.content.Context
import android.content.SharedPreferences
import java.util.UUID

/**
 * 管理本机设备身份信息。
 * device_id 首次启动生成，之后不再改变。
 * nickname 等用户资料也暂存于此（Phase 3 设置页会用到）。
 *
 * 对应 API 契约 §0.2：device_id 为客户端生成的 UUID v4。
 */
object DeviceManager {

    private const val PREFS_NAME = "note_passing_prefs"
    private const val KEY_DEVICE_ID = "device_id"
    private const val KEY_NICKNAME = "nickname"
    private const val KEY_PROFILE = "profile"
    private const val KEY_AVATAR = "avatar"
    private const val KEY_TAGS = "tags"
    private const val KEY_IS_ANONYMOUS = "is_anonymous"
    private const val KEY_ROLE_NAME = "role_name"
    private const val KEY_INITIALIZED = "initialized"

    private lateinit var prefs: SharedPreferences

    fun init(context: Context) {
        prefs = context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }

    /**
     * 获取 device_id，如果不存在则自动生成。
     * 生成后持久化，重启不变。
     */
    fun getDeviceId(): String {
        var id = prefs.getString(KEY_DEVICE_ID, null)
        if (id == null) {
            id = UUID.randomUUID().toString().replace("-", "")
            prefs.edit().putString(KEY_DEVICE_ID, id).apply()
        }
        return id
    }

    /** 首次引导是否完成（Phase 3 会用到） */
    fun isInitialized(): Boolean = prefs.getBoolean(KEY_INITIALIZED, false)
    fun setInitialized(value: Boolean) = prefs.edit().putBoolean(KEY_INITIALIZED, value).apply()

    fun getNickname(): String = prefs.getString(KEY_NICKNAME, "") ?: ""
    fun setNickname(value: String) = prefs.edit().putString(KEY_NICKNAME, value).apply()

    fun getProfile(): String = prefs.getString(KEY_PROFILE, "") ?: ""
    fun setProfile(value: String) = prefs.edit().putString(KEY_PROFILE, value).apply()

    fun getAvatar(): String? = prefs.getString(KEY_AVATAR, null)
    fun setAvatar(value: String?) = prefs.edit().putString(KEY_AVATAR, value).apply()

    fun getTags(): List<String> = TagSerializer.decode(prefs.getString(KEY_TAGS, "[]"))
    fun setTags(value: List<String>) {
        prefs.edit().putString(KEY_TAGS, TagSerializer.encode(value)).apply()
    }

    fun isAnonymous(): Boolean = prefs.getBoolean(KEY_IS_ANONYMOUS, false)
    fun setAnonymous(value: Boolean) = prefs.edit().putBoolean(KEY_IS_ANONYMOUS, value).apply()

    fun getRoleName(): String? = prefs.getString(KEY_ROLE_NAME, null)
    fun setRoleName(value: String?) = prefs.edit().putString(KEY_ROLE_NAME, value).apply()
}
