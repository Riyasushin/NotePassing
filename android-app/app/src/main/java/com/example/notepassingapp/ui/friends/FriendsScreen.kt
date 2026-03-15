package com.example.notepassingapp.ui.friends

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.notepassingapp.data.local.entity.FriendEntity
import com.example.notepassingapp.data.local.entity.FriendRequestEntity
import com.example.notepassingapp.ui.components.ProfileDetailDialog
import com.example.notepassingapp.ui.components.ProfilePreviewData
import com.example.notepassingapp.ui.theme.AppBackgroundWhite
import com.example.notepassingapp.util.TagSerializer

@Composable
fun FriendsScreen(
    onFriendClick: (String) -> Unit = {},
    viewModel: FriendsViewModel = viewModel()
) {
    val friends by viewModel.friends.collectAsState()
    val incomingRequests by viewModel.incomingRequests.collectAsState()
    val processingRequestIds by viewModel.processingRequestIds.collectAsState()
    val deletingFriendIds by viewModel.deletingFriendIds.collectAsState()
    var pendingDeleteFriend by remember { mutableStateOf<FriendEntity?>(null) }
    var selectedProfile by remember { mutableStateOf<ProfilePreviewData?>(null) }

    LaunchedEffect(Unit) {
        viewModel.refreshIncomingRequests()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(AppBackgroundWhite)
            .padding(horizontal = 16.dp)
    ) {
        Text(
            text = "好友",
            style = MaterialTheme.typography.headlineMedium,
            color = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.padding(top = 16.dp, bottom = 12.dp)
        )

        if (friends.isEmpty() && incomingRequests.isEmpty()) {
            // 空状态
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "还没有好友",
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = "在附近页发现新朋友吧",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.outline
                    )
                    // 测试用按钮，后续删除
                    Spacer(modifier = Modifier.height(24.dp))
                    OutlinedButton(onClick = { viewModel.insertTestFriends() }) {
                        Text("插入测试好友")
                    }
                }
            }
        } else {
            LazyColumn(
                contentPadding = PaddingValues(bottom = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                if (incomingRequests.isNotEmpty()) {
                    item {
                        Text(
                            text = "好友申请",
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.padding(bottom = 4.dp)
                        )
                    }
                    items(
                        items = incomingRequests,
                        key = { it.requestId }
                    ) { request ->
                        FriendRequestCard(
                            request = request,
                            processing = request.requestId in processingRequestIds,
                            onAccept = { viewModel.acceptFriendRequest(request.requestId) },
                            onReject = { viewModel.rejectFriendRequest(request.requestId) }
                        )
                    }
                }

                if (friends.isNotEmpty()) {
                    item {
                        Text(
                            text = "我的好友",
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.padding(top = if (incomingRequests.isNotEmpty()) 8.dp else 0.dp, bottom = 4.dp)
                        )
                    }
                }

                items(
                    items = friends,
                    key = { it.deviceId }
                ) { friend ->
                    FriendCard(
                        friend = friend,
                        isDeleting = friend.deviceId in deletingFriendIds,
                        onClick = { onFriendClick(friend.deviceId) },
                        onAvatarClick = {
                            selectedProfile = ProfilePreviewData(
                                avatarUrl = friend.avatar,
                                nickname = friend.nickname,
                                profile = friend.profile,
                                tags = TagSerializer.decode(friend.tags),
                                isFriend = true,
                            )
                        },
                        onDelete = { pendingDeleteFriend = friend }
                    )
                }
                if (friends.isNotEmpty()) {
                    item {
                        OutlinedButton(onClick = { viewModel.clearTestFriends() }) {
                            Text("清除测试数据")
                        }
                    }
                }
            }
        }
    }

    pendingDeleteFriend?.let { friend ->
        AlertDialog(
            onDismissRequest = { pendingDeleteFriend = null },
            title = { Text("确认删除好友") },
            text = { Text("删除 ${friend.nickname} 后，对方将从好友列表移除。") },
            confirmButton = {
                Button(
                    onClick = {
                        viewModel.deleteFriend(friend.deviceId)
                        pendingDeleteFriend = null
                    }
                ) {
                    Text("确认删除")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { pendingDeleteFriend = null }) {
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
}

@Composable
private fun FriendRequestCard(
    request: FriendRequestEntity,
    processing: Boolean,
    onAccept: () -> Unit,
    onReject: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceContainerLow
        )
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = request.peerNickname,
                style = MaterialTheme.typography.titleMedium
            )
            request.message?.takeIf { it.isNotBlank() }?.let { message ->
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = message,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(
                    onClick = onReject,
                    enabled = !processing
                ) {
                    Text("拒绝")
                }
                Button(
                    onClick = onAccept,
                    enabled = !processing
                ) {
                    Text(if (processing) "处理中" else "接受")
                }
            }
        }
    }
}
