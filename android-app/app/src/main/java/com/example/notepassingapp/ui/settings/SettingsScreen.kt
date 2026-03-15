package com.example.notepassingapp.ui.settings

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.notepassingapp.ui.components.ProfileTagChips
import com.example.notepassingapp.ui.components.UserAvatar
import com.example.notepassingapp.ui.theme.AppBackgroundWhite
import kotlinx.coroutines.launch

@Composable
fun SettingsScreen(
    onNavigateToDebug: () -> Unit = {},
    settingsViewModel: SettingsViewModel = viewModel()
) {
    val state by settingsViewModel.uiState.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val photoPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia()
    ) { uri ->
        if (uri != null) {
            settingsViewModel.uploadAvatar(uri)
        }
    }

    LaunchedEffect(state.transientMessage) {
        state.transientMessage?.let { message ->
            snackbarHostState.showSnackbar(message)
            settingsViewModel.consumeTransientMessage()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(AppBackgroundWhite)
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        Text(
            text = "设置",
            style = MaterialTheme.typography.headlineMedium,
            color = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.padding(bottom = 16.dp)
        )

        // --- 基本信息 ---
        SectionCard(title = "基本信息") {
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                UserAvatar(
                    avatarUrl = state.avatar.ifBlank { null },
                    isFriend = true,
                    size = 84.dp,
                    contentDescription = "我的头像",
                )

                Spacer(modifier = Modifier.height(12.dp))

                OutlinedButton(
                    onClick = {
                        photoPickerLauncher.launch(
                            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                        )
                    },
                    enabled = !state.isUploadingAvatar,
                    shape = RoundedCornerShape(12.dp),
                ) {
                    Text(if (state.isUploadingAvatar) "上传中..." else "从相册选择头像")
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            OutlinedTextField(
                value = state.nickname,
                onValueChange = { settingsViewModel.updateNickname(it) },
                label = { Text("昵称") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            )

            Spacer(modifier = Modifier.height(12.dp))

            OutlinedTextField(
                value = state.profile,
                onValueChange = { settingsViewModel.updateProfile(it) },
                label = { Text("简介") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            )

            Spacer(modifier = Modifier.height(12.dp))

            OutlinedTextField(
                value = state.tagsInput,
                onValueChange = { settingsViewModel.updateTagsInput(it) },
                label = { Text("标签") },
                placeholder = { Text("例如：#摄影 #徒步 #咖啡") },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            )

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = "输入时会自动补 #，标签之间用空格分隔；例如：#摄影 #徒步。",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            if (state.tags.isNotEmpty()) {
                Spacer(modifier = Modifier.height(10.dp))
                ProfileTagChips(
                    tags = state.tags,
                    modifier = Modifier.fillMaxWidth()
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            OutlinedTextField(
                value = state.avatar,
                onValueChange = { settingsViewModel.updateAvatar(it) },
                label = { Text("头像 URL") },
                readOnly = true,
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        // --- 隐私设置 ---
        SectionCard(title = "隐私设置") {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text("匿名模式", style = MaterialTheme.typography.bodyLarge)
                    Text(
                        "开启后附近的陌生人只会看到“不愿透露姓名的ta”，头像和资料都会隐藏",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Switch(
                    checked = state.isAnonymous,
                    onCheckedChange = { settingsViewModel.updateAnonymous(it) }
                )
            }

            if (state.isAnonymous) {
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedTextField(
                    value = state.roleName,
                    onValueChange = { settingsViewModel.updateRoleName(it) },
                    label = { Text("匿名角色名") },
                    placeholder = { Text("例如：神秘旅者") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // --- 设备信息 ---
        SectionCard(title = "设备信息") {
            Text(
                text = "Device ID",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                text = state.deviceId,
                style = MaterialTheme.typography.bodyMedium
            )
        }

        Spacer(modifier = Modifier.height(24.dp))

        // --- 保存按钮 ---
        TextButton(
            onClick = {
                settingsViewModel.save()
                scope.launch {
                    snackbarHostState.showSnackbar("已保存")
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("保存修改", style = MaterialTheme.typography.titleMedium)
        }

        Spacer(modifier = Modifier.height(12.dp))

        // --- 调试面板入口 ---
        OutlinedButton(
            onClick = onNavigateToDebug,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp)
        ) {
            Text("调试面板", style = MaterialTheme.typography.bodyMedium)
        }

        SnackbarHost(hostState = snackbarHostState)
    }
}

@Composable
private fun SectionCard(
    title: String,
    content: @Composable () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceContainerLow
        )
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.primary
            )
            HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))
            content()
        }
    }
}
