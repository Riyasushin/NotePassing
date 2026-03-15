package com.example.notepassingapp.ui.friends

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.TextButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.example.notepassingapp.data.local.entity.FriendEntity
import com.example.notepassingapp.ui.components.StatusPill
import com.example.notepassingapp.ui.components.UserAvatar
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun FriendCard(
    friend: FriendEntity,
    isDeleting: Boolean = false,
    onClick: () -> Unit,
    onAvatarClick: () -> Unit,
    onDelete: () -> Unit = {}
) {
    val style = friendCardStyle(friend)
    val shape = RoundedCornerShape(16.dp)
    Card(
        modifier = Modifier
            .then(
                if (style.borderBrush != null) {
                    Modifier.border(width = style.borderWidth, brush = style.borderBrush, shape = shape)
                } else {
                    Modifier
                }
            )
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = shape,
        colors = CardDefaults.cardColors(
            containerColor = style.containerColor
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                UserAvatar(
                    avatarUrl = friend.avatar,
                    isFriend = true,
                    size = 48.dp,
                    modifier = Modifier.clickable(onClick = onAvatarClick),
                    contentDescription = friend.nickname,
                )

                Spacer(modifier = Modifier.width(12.dp))

                // 文字信息
                Column(modifier = Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = friend.nickname,
                            style = MaterialTheme.typography.titleMedium,
                            color = style.titleColor,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.weight(1f, fill = false)
                        )
                        style.badgeText?.let { badgeText ->
                            Spacer(modifier = Modifier.width(6.dp))
                            StatusPill(
                                text = badgeText,
                                backgroundColor = style.badgeBackgroundColor,
                                contentColor = Color.White,
                            )
                        }
                    }

                    if (friend.profile.isNotBlank()) {
                        Text(
                            text = friend.profile,
                            style = MaterialTheme.typography.bodySmall,
                            color = style.secondaryTextColor,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                }

                // 右侧信息：见面次数 + 最后聊天时间
                Column(horizontalAlignment = Alignment.End) {
                    if (friend.meetCount > 0) {
                        Text(
                            text = "遇见 ${friend.meetCount} 次",
                            style = MaterialTheme.typography.labelSmall,
                            color = style.accentColor
                        )
                    }
                    friend.lastChatAt?.let {
                        Text(
                            text = formatTime(it),
                            style = MaterialTheme.typography.labelSmall,
                            color = style.secondaryTextColor
                        )
                    }
                    TextButton(
                        onClick = onDelete,
                        enabled = !isDeleting
                    ) {
                        Text(
                            text = if (isDeleting) "删除中" else "删除好友",
                            color = style.accentColor,
                        )
                    }
                }
            }
        }
    }
}

private fun formatTime(timestamp: Long): String {
    val now = System.currentTimeMillis()
    val diff = now - timestamp
    return when {
        diff < 60_000 -> "刚刚"
        diff < 3600_000 -> "${diff / 60_000}分钟前"
        diff < 86400_000 -> "${diff / 3600_000}小时前"
        else -> SimpleDateFormat("MM/dd", Locale.getDefault()).format(Date(timestamp))
    }
}

private data class FriendCardStyle(
    val containerColor: Color,
    val borderBrush: Brush? = null,
    val borderWidth: Dp = 0.dp,
    val badgeText: String? = null,
    val badgeBackgroundColor: Color = Color.Transparent,
    val titleColor: Color,
    val secondaryTextColor: Color,
    val accentColor: Color,
)

@Composable
private fun friendCardStyle(friend: FriendEntity): FriendCardStyle {
    val whiteBackground = Color(0xFFFFFFFF)
    val gold = Color(0xFFD7A63A)

    return FriendCardStyle(
        containerColor = whiteBackground,
        borderBrush = if (friend.isNearby) {
            Brush.linearGradient(listOf(gold, Color(0xFFF2D27A)))
        } else {
            null
        },
        borderWidth = if (friend.isNearby) 4.dp else 0.dp,
        badgeText = if (friend.isNearby) "在附近" else null,
        badgeBackgroundColor = if (friend.isNearby) gold else Color.Transparent,
        titleColor = Color(0xFF15181C),
        secondaryTextColor = Color(0xFF677281),
        accentColor = if (friend.isNearby) gold else Color(0xFF6A7280),
    )
}
