package com.example.notepassingapp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import com.example.notepassingapp.ui.navigation.MainNavHost
import com.example.notepassingapp.ui.theme.NotePassingAppTheme

/**
 * App 唯一的 Activity（单 Activity 架构）。
 * 所有页面切换都通过 Navigation Compose 在内部完成，不需要多个 Activity。
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            NotePassingAppTheme {
                MainNavHost()
            }
        }
    }
}
