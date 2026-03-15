package com.example.notepassingapp.ui.nearby

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.notepassingapp.ble.BleManager
import com.example.notepassingapp.ui.components.ProfileDetailDialog
import com.example.notepassingapp.ui.components.ProfilePreviewData

private val NearbyScreenBackground = Color(0xFF20252B)
private val NearbyScreenTitleColor = Color(0xFFF3F5F7)
private val NearbyScreenSubtitleColor = Color(0xFFBCC5CE)

@Composable
fun NearbyScreen(
    onUserClick: (String) -> Unit = {},
    viewModel: NearbyViewModel = viewModel()
) {
    val nearbyUsers by viewModel.nearbyUsers.collectAsState()
    val bleState by viewModel.bleState.collectAsState()
    val processingRequestIds by viewModel.processingRequestIds.collectAsState()
    val processingBlockIds by viewModel.processingBlockIds.collectAsState()
    val tagMatchCards by viewModel.tagMatchCards.collectAsState()
    val context = LocalContext.current
    var pendingBlockUser by remember { mutableStateOf<com.example.notepassingapp.data.model.NearbyUser?>(null) }
    var selectedProfile by remember { mutableStateOf<ProfilePreviewData?>(null) }

    var permissionsGranted by remember {
        mutableStateOf(checkBlePermissions(context))
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        permissionsGranted = results.values.all { it }
    }

    LaunchedEffect(permissionsGranted) {
        viewModel.ensureBleRunningWhenReady(permissionsGranted)
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(NearbyScreenBackground)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 16.dp)
        ) {
            Text(
                text = "附近",
                style = MaterialTheme.typography.headlineMedium,
                color = NearbyScreenTitleColor,
                modifier = Modifier.padding(top = 16.dp, bottom = 4.dp)
            )

            if (bleState.running) {
                BleStatusBar(bleState)
            }

            Spacer(modifier = Modifier.height(8.dp))

            if (!permissionsGranted) {
                PermissionCard(
                    onRequest = { permissionLauncher.launch(blePermissions()) }
                )
            } else if (!bleState.running) {
                StartBleCard(onStart = { viewModel.startBle() })
            }

            if (nearbyUsers.isEmpty() && !bleState.running) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "附近暂无用户",
                            style = MaterialTheme.typography.titleMedium,
                            color = NearbyScreenTitleColor
                        )
                        Text(
                            text = "打开蓝牙，发现身边的人",
                            style = MaterialTheme.typography.bodyMedium,
                            color = NearbyScreenSubtitleColor
                        )
                    }
                }
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(bottom = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(
                        items = nearbyUsers,
                        key = { it.deviceId }
                    ) { user ->
                        NearbyCard(
                            user = user,
                            isFriendRequestProcessing = user.deviceId in processingRequestIds,
                            isBlockProcessing = user.deviceId in processingBlockIds,
                            onClick = { onUserClick(user.deviceId) },
                            onAvatarClick = {
                                selectedProfile = ProfilePreviewData(
                                    avatarUrl = user.displayAvatar,
                                    nickname = user.displayNickname,
                                    profile = user.displayProfile,
                                    tags = user.displayTags,
                                    isFriend = user.isFriend,
                                    isIdentityHidden = user.isIdentityHidden,
                                )
                            },
                            onAddFriend = { viewModel.sendFriendRequest(user) },
                            onBlock = { pendingBlockUser = user }
                        )
                    }
                    if (nearbyUsers.isNotEmpty()) {
                        item {
                            if (bleState.running) {
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    OutlinedButton(onClick = { viewModel.stopBle() }) {
                                        Text("停止 BLE")
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

    }

    pendingBlockUser?.let { user ->
        AlertDialog(
            onDismissRequest = { pendingBlockUser = null },
            title = { Text("确认拉黑") },
            text = { Text("拉黑 ${user.displayNickname} 后，对方将从附近页隐藏。") },
            confirmButton = {
                Button(
                    onClick = {
                        viewModel.blockUser(user)
                        pendingBlockUser = null
                    }
                ) {
                    Text("确认拉黑")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { pendingBlockUser = null }) {
                    Text("取消")
                }
            }
        )
    }

    selectedProfile?.let { preview ->
        ProfileDetailDialog(
            preview = preview,
            onDismiss = { selectedProfile = null },
        )
    }

    tagMatchCards.firstOrNull()?.let { card ->
        TagMatchFloatingCard(
            card = card,
            queueSize = tagMatchCards.size,
            onOpenChat = onUserClick,
            onIgnore = { viewModel.ignoreCurrentTagMatch() },
            onCloseAll = { viewModel.clearAllTagMatches() },
        )
    }
}

@Composable
private fun BleStatusBar(state: BleManager.State) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        )
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                if (state.isScanning) "扫描中…" else "等待扫描",
                style = MaterialTheme.typography.labelMedium
            )
            Text(
                "发现 ${state.foundCount} 台",
                style = MaterialTheme.typography.labelMedium
            )
            if (state.tempId != null) {
                Text(
                    "ID: ${state.tempId.take(8)}…",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                )
            }
        }
    }
}

@Composable
private fun PermissionCard(onRequest: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.errorContainer
        )
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                "需要蓝牙和位置权限",
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onErrorContainer
            )
            Text(
                "NotePassing 使用蓝牙发现附近的人，需要相关权限才能正常工作。",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onErrorContainer.copy(alpha = 0.8f)
            )
            Spacer(modifier = Modifier.height(8.dp))
            Button(onClick = onRequest) { Text("授予权限") }
        }
    }
}

@Composable
private fun StartBleCard(onStart: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("蓝牙发现已就绪", style = MaterialTheme.typography.titleSmall)
            Spacer(modifier = Modifier.height(8.dp))
            Button(onClick = onStart) { Text("开始发现附近的人") }
        }
    }
}

private fun checkBlePermissions(context: android.content.Context): Boolean {
    return blePermissions().all {
        ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
    }
}

private fun blePermissions(): Array<String> {
    val perms = mutableListOf<String>()
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        perms.add(Manifest.permission.BLUETOOTH_SCAN)
        perms.add(Manifest.permission.BLUETOOTH_ADVERTISE)
        perms.add(Manifest.permission.BLUETOOTH_CONNECT)
    }
    perms.add(Manifest.permission.ACCESS_FINE_LOCATION)
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        perms.add(Manifest.permission.POST_NOTIFICATIONS)
    }
    return perms.toTypedArray()
}
