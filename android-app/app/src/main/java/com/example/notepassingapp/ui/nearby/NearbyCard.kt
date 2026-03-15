package com.example.notepassingapp.ui.nearby

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.example.notepassingapp.data.model.FriendRequestState
import com.example.notepassingapp.data.model.NearbyState
import com.example.notepassingapp.data.model.NearbyUser
import com.example.notepassingapp.ui.components.ProfileTagChips
import com.example.notepassingapp.ui.components.StatusPill
import com.example.notepassingapp.ui.components.UserAvatar
import kotlinx.coroutines.delay

@Composable
fun NearbyCard(
    user: NearbyUser,
    isFriendRequestProcessing: Boolean = false,
    isBlockProcessing: Boolean = false,
    onClick: () -> Unit,
    onAvatarClick: () -> Unit,
    onAddFriend: () -> Unit = {},
    onBlock: () -> Unit = {}
) {
    val isGrace = user.state == NearbyState.GRACE
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
    val style = nearbyCardStyle(user)
    val shape = RoundedCornerShape(16.dp)

    Card(
        modifier = Modifier
            .nearbyAccentBorders(shapeRadius = 16.dp, borders = style.borders)
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
                .padding(12.dp),
            verticalAlignment = Alignment.Top
        ) {
            UserAvatar(
                avatarUrl = user.displayAvatar,
                isFriend = user.isFriend,
                size = 52.dp,
                modifier = Modifier.clickable(onClick = onAvatarClick),
                contentDescription = user.displayNickname,
            )

            Spacer(modifier = Modifier.width(12.dp))

            // 中间文字区
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = user.displayNickname,
                        style = MaterialTheme.typography.titleMedium,
                        color = style.titleColor,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f, fill = false)
                    )
                    style.badgeText?.let { badgeText ->
                        Spacer(modifier = Modifier.width(4.dp))
                        StatusPill(
                            text = badgeText,
                            backgroundColor = style.badgeBackgroundColor,
                            contentColor = Color.White,
                        )
                    }
                }

                if (user.displayTags.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(6.dp))
                    ProfileTagChips(
                        tags = user.displayTags,
                        maxVisible = 3,
                    )
                }

                // 最后一条消息预览
                user.displayLastMessage?.let { msg ->
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = msg,
                        style = MaterialTheme.typography.bodySmall,
                        color = style.secondaryTextColor,
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
                        color = style.accentColor
                    )
                } else {
                    Text(
                        text = if (user.state == NearbyState.EXPIRED) {
                            user.signalStrengthLabel
                        } else {
                            "蓝牙强度 ${user.signalStrengthLabel}"
                        },
                        style = MaterialTheme.typography.labelSmall,
                        color = style.accentColor
                    )
                }

                user.displayLastMessageAt?.let {
                    Text(
                        text = formatRelativeTime(it),
                        style = MaterialTheme.typography.labelSmall,
                        color = style.secondaryTextColor
                    )
                }

                if (!user.isFriend) {
                    Column(horizontalAlignment = Alignment.End) {
                        TextButton(
                            onClick = onAddFriend,
                            enabled = !isFriendRequestProcessing && user.friendRequestState == FriendRequestState.NONE,
                            modifier = Modifier.padding(top = 4.dp)
                        ) {
                            Text(
                                text = friendActionLabel(user.friendRequestState, isFriendRequestProcessing),
                                color = style.accentColor,
                            )
                        }

                        TextButton(
                            onClick = onBlock,
                            enabled = !isBlockProcessing
                        ) {
                            Text(
                                text = if (isBlockProcessing) "拉黑中" else "拉黑",
                                color = style.secondaryTextColor,
                            )
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

private data class NearbyCardBorderSpec(
    val brush: Brush,
    val width: Dp,
)

private data class NearbyCardStyle(
    val containerColor: Color,
    val borders: List<NearbyCardBorderSpec> = emptyList(),
    val badgeText: String? = null,
    val badgeBackgroundColor: Color = Color.Transparent,
    val titleColor: Color,
    val secondaryTextColor: Color,
    val accentColor: Color,
)

@Composable
private fun nearbyCardStyle(user: NearbyUser): NearbyCardStyle {
    val activeBackground = Color(0xFFFFFFFF)
    val graceBackground = Color(0xFFE7EAEE)
    val expiredBackground = Color(0xFF181B1F)
    val whiteBackground = Color(0xFFFFFFFF)
    val green = Color(0xFF2E9B57)
    val blue = Color(0xFF2F80ED)
    val gold = Color(0xFFD7A63A)
    val greenBrush = Brush.linearGradient(listOf(green, Color(0xFF6DCE8D)))
    val blueBrush = Brush.linearGradient(listOf(blue, Color(0xFF72B2FF)))
    val goldBrush = Brush.linearGradient(listOf(gold, Color(0xFFF2D27A)))

    val containerColor = when (user.state) {
        NearbyState.EXPIRED -> expiredBackground
        NearbyState.GRACE -> graceBackground
        NearbyState.ACTIVE -> activeBackground
    }

    val borders = when {
        user.isFriend -> listOf(
            NearbyCardBorderSpec(
                brush = goldBrush,
                width = 4.dp,
            )
        )
        user.state == NearbyState.ACTIVE && user.hasCommonTags -> listOf(
            NearbyCardBorderSpec(
                brush = greenBrush,
                width = 4.dp,
            ),
            NearbyCardBorderSpec(
                brush = blueBrush,
                width = 4.dp,
            ),
        )
        user.state == NearbyState.ACTIVE -> listOf(
            NearbyCardBorderSpec(
                brush = greenBrush,
                width = 4.dp,
            )
        )
        user.hasCommonTags -> listOf(
            NearbyCardBorderSpec(
                brush = blueBrush,
                width = 4.dp,
            )
        )
        else -> emptyList()
    }

    val isDark = user.state == NearbyState.EXPIRED
    return NearbyCardStyle(
        containerColor = if (user.state == NearbyState.ACTIVE && user.isFriend) whiteBackground else containerColor,
        borders = borders,
        badgeText = if (user.isFriend) "好友" else null,
        badgeBackgroundColor = if (user.isFriend) gold else Color.Transparent,
        titleColor = if (isDark) Color(0xFFF7F8FA) else Color(0xFF15181C),
        secondaryTextColor = if (isDark) Color(0xFFD2D8E0) else Color(0xFF677281),
        accentColor = when {
            user.isFriend -> gold
            user.hasCommonTags -> blue
            !user.isFriend && user.state == NearbyState.ACTIVE -> green
            else -> if (isDark) Color(0xFFD2D8E0) else Color(0xFF6A7280)
        },
    )
}

private fun Modifier.nearbyAccentBorders(
    shapeRadius: Dp,
    borders: List<NearbyCardBorderSpec>,
): Modifier {
    if (borders.isEmpty()) return this

    return drawWithContent {
        drawContent()

        val gapPx = 2.dp.toPx()
        val baseRadiusPx = shapeRadius.toPx()
        var consumedPx = 0f

        borders.forEach { border ->
            val strokePx = border.width.toPx()
            val insetPx = consumedPx + strokePx / 2f
            val drawWidth = size.width - insetPx * 2f
            val drawHeight = size.height - insetPx * 2f

            if (drawWidth > 0f && drawHeight > 0f) {
                val radiusPx = (baseRadiusPx - insetPx).coerceAtLeast(0f)
                drawRoundRect(
                    brush = border.brush,
                    topLeft = Offset(insetPx, insetPx),
                    size = Size(drawWidth, drawHeight),
                    cornerRadius = CornerRadius(radiusPx, radiusPx),
                    style = Stroke(width = strokePx),
                )
            }

            consumedPx += strokePx + gapPx
        }
    }
}
