package com.example.notepassingapp.ui.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.ui.unit.dp
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.notepassingapp.ui.chat.ChatScreen
import com.example.notepassingapp.ui.chat.ChatViewModel
import com.example.notepassingapp.ui.debug.DebugScreen
import com.example.notepassingapp.ui.friends.FriendsScreen
import com.example.notepassingapp.ui.nearby.NearbyScreen
import com.example.notepassingapp.ui.onboarding.OnboardingScreen
import com.example.notepassingapp.ui.settings.SettingsScreen
import com.example.notepassingapp.util.DeviceManager

private const val ROUTE_ONBOARDING = "onboarding"
private const val ROUTE_CHAT = "chat/{peerDeviceId}"
private const val ROUTE_DEBUG = "debug"

fun chatRoute(peerDeviceId: String) = "chat/$peerDeviceId"

@Composable
fun MainNavHost() {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route

    val startDestination = if (DeviceManager.isInitialized()) {
        BottomNavItem.Nearby.route
    } else {
        ROUTE_ONBOARDING
    }

    // 底部栏只在三个主页面显示，聊天页和引导页不显示
    val showBottomBar = currentRoute in BottomNavItem.entries.map { it.route }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        bottomBar = {
            if (showBottomBar) {
                NavigationBar(
                    containerColor = MaterialTheme.colorScheme.surface,
                    tonalElevation = 0.dp,
                ) {
                    BottomNavItem.entries.forEach { item ->
                        NavigationBarItem(
                            selected = currentRoute == item.route,
                            onClick = {
                                navController.navigate(item.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { Icon(item.icon, contentDescription = item.label) },
                            label = { Text(item.label) }
                        )
                    }
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = startDestination,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(ROUTE_ONBOARDING) {
                OnboardingScreen(
                    onComplete = {
                        navController.navigate(BottomNavItem.Nearby.route) {
                            popUpTo(ROUTE_ONBOARDING) { inclusive = true }
                        }
                    }
                )
            }

            composable(BottomNavItem.Nearby.route) {
                NearbyScreen(
                    onUserClick = { deviceId ->
                        navController.navigate(chatRoute(deviceId))
                    }
                )
            }

            composable(BottomNavItem.Friends.route) {
                FriendsScreen(
                    onFriendClick = { deviceId ->
                        navController.navigate(chatRoute(deviceId))
                    }
                )
            }

            composable(BottomNavItem.Settings.route) {
                SettingsScreen(
                    onNavigateToDebug = { navController.navigate(ROUTE_DEBUG) }
                )
            }

            composable(ROUTE_DEBUG) {
                DebugScreen(onBack = { navController.popBackStack() })
            }

            // 聊天页：从路由参数取 peerDeviceId，用 Factory 创建带参数的 ViewModel
            composable(
                route = ROUTE_CHAT,
                arguments = listOf(navArgument("peerDeviceId") { type = NavType.StringType })
            ) { entry ->
                val peerDeviceId = entry.arguments?.getString("peerDeviceId") ?: return@composable
                val chatViewModel: ChatViewModel = viewModel(
                    factory = ChatViewModel.Factory(peerDeviceId)
                )
                ChatScreen(
                    peerDeviceId = peerDeviceId,
                    onBack = { navController.popBackStack() },
                    viewModel = chatViewModel
                )
            }
        }
    }
}
