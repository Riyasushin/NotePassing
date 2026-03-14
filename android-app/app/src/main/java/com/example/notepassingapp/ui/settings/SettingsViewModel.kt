package com.example.notepassingapp.ui.settings

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.notepassingapp.data.repository.DeviceRepository
import com.example.notepassingapp.util.DeviceManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class SettingsUiState(
    val deviceId: String = "",
    val nickname: String = "",
    val avatar: String = "",
    val profile: String = "",
    val isAnonymous: Boolean = false,
    val roleName: String = "",
    val isSyncing: Boolean = false
)

class SettingsViewModel : ViewModel() {

    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    init {
        loadFromLocal()
    }

    private fun loadFromLocal() {
        _uiState.value = SettingsUiState(
            deviceId = DeviceManager.getDeviceId(),
            nickname = DeviceManager.getNickname(),
            avatar = DeviceManager.getAvatar().orEmpty(),
            profile = DeviceManager.getProfile(),
            isAnonymous = DeviceManager.isAnonymous(),
            roleName = DeviceManager.getRoleName() ?: ""
        )
    }

    fun updateNickname(value: String) {
        _uiState.value = _uiState.value.copy(nickname = value)
    }

    fun updateProfile(value: String) {
        _uiState.value = _uiState.value.copy(profile = value)
    }

    fun updateAvatar(value: String) {
        _uiState.value = _uiState.value.copy(avatar = value)
    }

    fun updateAnonymous(value: Boolean) {
        _uiState.value = _uiState.value.copy(isAnonymous = value)
    }

    fun updateRoleName(value: String) {
        _uiState.value = _uiState.value.copy(roleName = value)
    }

    /** 保存到本地 + 异步同步到服务器 */
    fun save() {
        val state = _uiState.value
        DeviceManager.setNickname(state.nickname)
        DeviceManager.setAvatar(state.avatar.ifBlank { null })
        DeviceManager.setProfile(state.profile)
        DeviceManager.setAnonymous(state.isAnonymous)
        DeviceManager.setRoleName(state.roleName.ifBlank { null })

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSyncing = true)
            val result = DeviceRepository.syncProfile()
            _uiState.value = _uiState.value.copy(isSyncing = false)
            Log.d("SettingsViewModel", "Profile sync: $result")
        }
    }

    /** 首次引导完成：保存并标记已初始化 */
    fun completeOnboarding() {
        val state = _uiState.value
        DeviceManager.setNickname(state.nickname)
        DeviceManager.setAvatar(state.avatar.ifBlank { null })
        DeviceManager.setProfile(state.profile)
        DeviceManager.setAnonymous(state.isAnonymous)
        DeviceManager.setRoleName(state.roleName.ifBlank { null })
        DeviceManager.setInitialized(true)
    }
}
