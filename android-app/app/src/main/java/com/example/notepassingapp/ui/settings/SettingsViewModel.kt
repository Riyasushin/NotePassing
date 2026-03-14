package com.example.notepassingapp.ui.settings

import androidx.lifecycle.ViewModel
import com.example.notepassingapp.util.DeviceManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

data class SettingsUiState(
    val deviceId: String = "",
    val nickname: String = "",
    val profile: String = "",
    val isAnonymous: Boolean = false,
    val roleName: String = ""
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

    fun updateAnonymous(value: Boolean) {
        _uiState.value = _uiState.value.copy(isAnonymous = value)
    }

    fun updateRoleName(value: String) {
        _uiState.value = _uiState.value.copy(roleName = value)
    }

    /** 保存所有设置到本地 */
    fun save() {
        val state = _uiState.value
        DeviceManager.setNickname(state.nickname)
        DeviceManager.setProfile(state.profile)
        DeviceManager.setAnonymous(state.isAnonymous)
        DeviceManager.setRoleName(state.roleName.ifBlank { null })
    }

    /** 首次引导完成：保存并标记已初始化 */
    fun completeOnboarding() {
        save()
        DeviceManager.setInitialized(true)
    }
}
