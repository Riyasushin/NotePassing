package com.example.notepassingapp.ui.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.PersonSearch
import androidx.compose.material.icons.filled.Settings
import androidx.compose.ui.graphics.vector.ImageVector

/**
 * 底部导航栏的三个 Tab 定义。
 * 每个 Tab 有：路由名(route)、显示标题(label)、图标(icon)。
 * route 用于 Navigation Compose 做页面切换。
 */
enum class BottomNavItem(
    val route: String,
    val label: String,
    val icon: ImageVector
) {
    Nearby(route = "nearby", label = "附近", icon = Icons.Default.PersonSearch),
    Friends(route = "friends", label = "好友", icon = Icons.Default.People),
    Settings(route = "settings", label = "设置", icon = Icons.Default.Settings)
}
