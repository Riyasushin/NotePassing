package com.example.notepassingapp.ui.nearby

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.notepassingapp.ble.BleManager

@Composable
fun NearbyScreen(
    onUserClick: (String) -> Unit = {},
    viewModel: NearbyViewModel = viewModel()
) {
    val nearbyUsers by viewModel.nearbyUsers.collectAsState()
    val bleState by viewModel.bleState.collectAsState()
    val context = LocalContext.current

    var permissionsGranted by remember {
        mutableStateOf(checkBlePermissions(context))
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        permissionsGranted = results.values.all { it }
        if (permissionsGranted) {
            viewModel.startBle()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp)
    ) {
        Text(
            text = "附近",
            style = MaterialTheme.typography.headlineMedium,
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
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = "打开蓝牙，发现身边的人",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.outline
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                    OutlinedButton(onClick = { viewModel.insertTestData() }) {
                        Text("插入测试数据")
                    }
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
                        onClick = { onUserClick(user.deviceId) }
                    )
                }
                if (nearbyUsers.isNotEmpty()) {
                    item {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(onClick = { viewModel.clearTestData() }) {
                                Text("清除测试数据")
                            }
                            if (bleState.running) {
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
