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
import com.example.notepassingapp.ui.onboarding.OnboardingScreen
import com.example.notepassingapp.ui.settings.SettingsScreen
import com.example.notepassingapp.util.DeviceManager

private const val ROUTE_ONBOARDING = "onboarding"

/**
 * App 的主导航骨架。
 * 启动时根据 isInitialized 决定显示引导页还是主页。
 * 引导页完成后跳转到主页，并清除引导页栈（不允许返回引导页）。
 */
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

    val showBottomBar = currentRoute in BottomNavItem.entries.map { it.route }

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NavigationBar {
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
                        // 跳转到附近页，同时把引导页从栈里清掉
                        navController.navigate(BottomNavItem.Nearby.route) {
                            popUpTo(ROUTE_ONBOARDING) { inclusive = true }
                        }
                    }
                )
            }
            composable(BottomNavItem.Nearby.route) { NearbyScreen() }
            composable(BottomNavItem.Friends.route) { FriendsScreen() }
            composable(BottomNavItem.Settings.route) { SettingsScreen() }
        }
    }
}
