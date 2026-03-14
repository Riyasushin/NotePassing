package com.example.notepassingapp.ui.debug

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DebugScreen(
    onBack: () -> Unit,
    viewModel: DebugViewModel = viewModel()
) {
    val logs by viewModel.logs.collectAsState()
    val wsState by viewModel.wsState.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val listState = rememberLazyListState()

    LaunchedEffect(logs.size) {
        if (logs.isNotEmpty()) {
            listState.animateScrollToItem(logs.size - 1)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("调试面板") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回")
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.clearLogs() }) {
                        Icon(Icons.Default.Delete, contentDescription = "清除日志")
                    }
                }
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            // --- 状态栏 ---
            StatusBar(wsState = wsState, isLoading = isLoading)

            HorizontalDivider()

            // --- API 测试按钮 ---
            ApiTestButtons(
                isLoading = isLoading,
                onDeviceInit = { viewModel.testDeviceInit() },
                onSyncProfile = { viewModel.testSyncProfile() },
                onRefreshTempId = { viewModel.testRefreshTempId() },
                onSyncFriends = { viewModel.testSyncFriends() },
                onWsConnect = { viewModel.testWsConnect() },
                onWsDisconnect = { viewModel.testWsDisconnect() },
                onWsPing = { viewModel.testWsPing() }
            )

            HorizontalDivider()

            // --- 日志区 ---
            LazyColumn(
                state = listState,
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color(0xFF1E1E1E))
                    .padding(8.dp)
            ) {
                items(logs) { entry ->
                    LogEntryRow(entry)
                }
            }
        }
    }
}

@Composable
private fun StatusBar(wsState: String, isLoading: Boolean) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            val color = when (wsState) {
                "CONNECTED" -> Color(0xFF4CAF50)
                "CONNECTING", "RECONNECTING" -> Color(0xFFFFC107)
                else -> Color(0xFFF44336)
            }
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .background(color, RoundedCornerShape(5.dp))
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "WS: $wsState",
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Bold
            )
        }
        if (isLoading) {
            CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
        }
    }
}

@Composable
private fun ApiTestButtons(
    isLoading: Boolean,
    onDeviceInit: () -> Unit,
    onSyncProfile: () -> Unit,
    onRefreshTempId: () -> Unit,
    onSyncFriends: () -> Unit,
    onWsConnect: () -> Unit,
    onWsDisconnect: () -> Unit,
    onWsPing: () -> Unit
) {
    Column(modifier = Modifier.padding(8.dp)) {
        Text(
            "REST API",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(start = 4.dp, bottom = 4.dp)
        )
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            DebugButton("device/init", isLoading, onDeviceInit)
            DebugButton("sync profile", isLoading, onSyncProfile)
            DebugButton("refresh tempId", isLoading, onRefreshTempId)
            DebugButton("sync friends", isLoading, onSyncFriends)
        }

        Spacer(modifier = Modifier.height(6.dp))

        Text(
            "WebSocket",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(start = 4.dp, bottom = 4.dp)
        )
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            DebugButton("WS 连接", isLoading, onWsConnect)
            DebugButton("WS 断开", isLoading, onWsDisconnect)
            DebugButton("WS Ping", isLoading, onWsPing)
        }
    }
}

@Composable
private fun DebugButton(text: String, isLoading: Boolean, onClick: () -> Unit) {
    FilledTonalButton(
        onClick = onClick,
        enabled = !isLoading,
        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
        shape = RoundedCornerShape(8.dp)
    ) {
        Text(text, fontSize = 12.sp)
    }
}

@Composable
private fun LogEntryRow(entry: LogEntry) {
    val tagColor = when (entry.tag) {
        "请求" -> Color(0xFF64B5F6)
        "响应" -> Color(0xFF81C784)
        "错误" -> Color(0xFFE57373)
        "WebSocket" -> Color(0xFFFFD54F)
        "配置" -> Color(0xFFB0BEC5)
        "设备" -> Color(0xFFCE93D8)
        else -> Color(0xFF90A4AE)
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp)
    ) {
        Text(
            text = entry.time,
            color = Color(0xFF757575),
            fontSize = 10.sp,
            fontFamily = FontFamily.Monospace
        )
        Spacer(modifier = Modifier.width(6.dp))
        Text(
            text = "[${entry.tag}]",
            color = tagColor,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace
        )
        Spacer(modifier = Modifier.width(6.dp))
        Text(
            text = entry.message,
            color = if (entry.isError) Color(0xFFE57373) else Color(0xFFE0E0E0),
            fontSize = 11.sp,
            fontFamily = FontFamily.Monospace
        )
    }
}
