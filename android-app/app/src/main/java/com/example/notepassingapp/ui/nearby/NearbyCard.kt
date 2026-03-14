package com.example.notepassingapp.ui.nearby

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.TextButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.example.notepassingapp.data.model.FriendRequestState
import com.example.notepassingapp.data.model.NearbyState
import com.example.notepassingapp.data.model.NearbyUser
import com.example.notepassingapp.ui.components.UserAvatar
import kotlinx.coroutines.delay

@Composable
fun NearbyCard(
    user: NearbyUser,
    isFriendRequestProcessing: Boolean = false,
    isBlockProcessing: Boolean = false,
    onClick: () -> Unit,
    onAddFriend: () -> Unit = {},
    onBlock: () -> Unit = {}
) {
    val isGrace = user.state == NearbyState.GRACE
    val contentAlpha = if (isGrace) 0.5f else 1f
    val graceRemainingSeconds by produceState(
        initialValue = calculateGraceRemainingSeconds(user.leftAt),
        key1 = isGrace,
        key2 = user.leftAt
    ) {
        if (!isGrace || user.leftAt == null) return@produceState

        while (true) {
            val remaining = calculateGraceRemainingSeconds(user.leftAt)
            value = remaining
            if (remaining <= 0) break
            delay(1000)
        }
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceContainerLow
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp)
                .alpha(contentAlpha),
            verticalAlignment = Alignment.Top
        ) {
            UserAvatar(
                avatarUrl = user.displayAvatar,
                isFriend = user.isFriend,
                size = 52.dp,
                contentDescription = user.displayNickname,
            )

            Spacer(modifier = Modifier.width(12.dp))

            // 中间文字区
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = user.displayNickname,
                        style = MaterialTheme.typography.titleMedium,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f, fill = false)
                    )
                    if (user.isFriend) {
                        Spacer(modifier = Modifier.width(4.dp))
                        Icon(
                            Icons.Default.Star,
                            contentDescription = "好友",
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }

                if (user.displayProfile.isNotBlank()) {
                    Text(
                        text = user.displayProfile,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }

                // 最后一条消息预览
                user.displayLastMessage?.let { msg ->
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = msg,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }

            Spacer(modifier = Modifier.width(8.dp))

            // 右侧状态信息
            Column(
                horizontalAlignment = Alignment.End,
                verticalArrangement = Arrangement.spacedBy(2.dp)
            ) {
                if (isGrace) {
                    Text(
                        text = "可聊天 ${graceRemainingSeconds}s",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.error
                    )
                } else {
                    Text(
                        text = "${String.format("%.1f", user.distanceEstimate)}m",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary
                    )
                }

                user.displayLastMessageAt?.let {
                    Text(
                        text = formatRelativeTime(it),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.outline
                    )
                }

                if (!user.isFriend) {
                    Column(horizontalAlignment = Alignment.End) {
                        TextButton(
                            onClick = onAddFriend,
                            enabled = !isFriendRequestProcessing && user.friendRequestState == FriendRequestState.NONE,
                            modifier = Modifier.padding(top = 4.dp)
                        ) {
                            Text(friendActionLabel(user.friendRequestState, isFriendRequestProcessing))
                        }

                        TextButton(
                            onClick = onBlock,
                            enabled = !isBlockProcessing
                        ) {
                            Text(if (isBlockProcessing) "拉黑中" else "拉黑")
                        }
                    }
                }
            }
        }
    }
}

private fun friendActionLabel(
    state: FriendRequestState,
    isProcessing: Boolean
): String {
    return when {
        isProcessing -> "发送中"
        state == FriendRequestState.OUTGOING_PENDING -> "已申请"
        state == FriendRequestState.INCOMING_PENDING -> "待处理"
        else -> "加好友"
    }
}

private fun calculateGraceRemainingSeconds(leftAt: Long?): Int {
    if (leftAt == null) return 60
    val elapsedSeconds = ((System.currentTimeMillis() - leftAt) / 1000).toInt()
    return maxOf(0, 60 - elapsedSeconds)
}

private fun formatRelativeTime(timestamp: Long): String {
    val diff = System.currentTimeMillis() - timestamp
    return when {
        diff < 60_000 -> "刚刚"
        diff < 3600_000 -> "${diff / 60_000}分钟前"
        diff < 86400_000 -> "${diff / 3600_000}小时前"
        else -> "${diff / 86400_000}天前"
    }
}
