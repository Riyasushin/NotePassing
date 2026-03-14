package com.example.notepassingapp.ui.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.example.notepassingapp.ui.friends.FriendsScreen
import com.example.notepassingapp.ui.nearby.NearbyScreen
import com.example.notepassingapp.ui.settings.SettingsScreen

/**
 * App 的主骨架：Scaffold（脚手架）包含底部导航栏 + 页面内容区。
 *
 * - NavController：导航控制器，记录当前在哪个页面、管理页面栈
 * - NavHost：根据当前路由渲染对应的 Screen
 * - NavigationBar：Material3 底部导航栏
 */
@Composable
fun MainNavHost() {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route

    Scaffold(
        bottomBar = {
            NavigationBar {
                BottomNavItem.entries.forEach { item ->
                    NavigationBarItem(
                        selected = currentRoute == item.route,
                        onClick = {
                            navController.navigate(item.route) {
                                // popUpTo: 点击 Tab 时不会无限叠加页面栈
                                // 而是回到起始页，再切换到目标页
                                popUpTo(navController.graph.findStartDestination().id) {
                                    saveState = true
                                }
                                launchSingleTop = true  // 不重复创建同一页面
                                restoreState = true     // 恢复之前的滚动位置等状态
                            }
                        },
                        icon = { Icon(item.icon, contentDescription = item.label) },
                        label = { Text(item.label) }
                    )
                }
            }
        }
    ) { innerPadding ->
        // NavHost：页面容器，根据路由显示对应 Screen
        // startDestination 决定 App 打开后默认显示哪个页面
        NavHost(
            navController = navController,
            startDestination = BottomNavItem.Nearby.route,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(BottomNavItem.Nearby.route) { NearbyScreen() }
            composable(BottomNavItem.Friends.route) { FriendsScreen() }
            composable(BottomNavItem.Settings.route) { SettingsScreen() }
        }
    }
}
