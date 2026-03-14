package com.example.notepassingapp.ui.chat

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.TextButton
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.notepassingapp.data.model.FriendRequestState
import com.example.notepassingapp.util.DeviceManager

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    peerDeviceId: String,
    onBack: () -> Unit,
    viewModel: ChatViewModel
) {
    val uiState by viewModel.uiState.collectAsState()
    val messages by viewModel.messages.collectAsState()
    val myDeviceId = DeviceManager.getDeviceId()
    val listState = rememberLazyListState()

    // 新消息到达时自动滚到底部
    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(uiState.peerNickname) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回")
                    }
                },
                actions = {
                    if (!uiState.isFriend) {
                        FriendActionButton(
                            state = uiState.friendRequestState,
                            loading = uiState.isFriendActionLoading,
                            onClick = { viewModel.sendFriendRequest() }
                        )
                    }
                }
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .imePadding()  // 键盘弹出时自动上推
        ) {
            uiState.friendStatusMessage?.let { msg ->
                Text(
                    text = msg,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
                )
            }

            // 消息列表
            LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(
                    items = messages,
                    key = { it.messageId }
                ) { msg ->
                    ChatBubble(
                        message = msg,
                        isMine = msg.senderId == myDeviceId
                    )
                }
            }

            // 发送限制提示
            uiState.sendLimitMessage?.let { msg ->
                Text(
                    text = msg,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
                )
            }

            // 输入框
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 8.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedTextField(
                    value = uiState.inputText,
                    onValueChange = { viewModel.updateInput(it) },
                    placeholder = { Text("输入消息...") },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(24.dp),
                    singleLine = false,
                    maxLines = 4,
                    enabled = uiState.canSend
                )

                IconButton(
                    onClick = { viewModel.sendMessage() },
                    enabled = uiState.canSend && uiState.inputText.isNotBlank()
                ) {
                    Icon(
                        Icons.AutoMirrored.Filled.Send,
                        contentDescription = "发送",
                        tint = if (uiState.canSend && uiState.inputText.isNotBlank())
                            MaterialTheme.colorScheme.primary
                        else
                            MaterialTheme.colorScheme.outline
                    )
                }
            }
        }
    }
}

@Composable
private fun FriendActionButton(
    state: FriendRequestState,
    loading: Boolean,
    onClick: () -> Unit
) {
    val label = when {
        loading -> "发送中"
        state == FriendRequestState.OUTGOING_PENDING -> "已申请"
        state == FriendRequestState.INCOMING_PENDING -> "待处理"
        else -> "加好友"
    }
    val enabled = !loading && state == FriendRequestState.NONE

    TextButton(onClick = onClick, enabled = enabled) {
        Text(label)
    }
}
