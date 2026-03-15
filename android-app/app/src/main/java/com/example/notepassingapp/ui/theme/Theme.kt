package com.example.notepassingapp.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val FixedColorScheme = lightColorScheme(
    primary = AppBlue,
    secondary = AppGreen,
    tertiary = AppGold,
    background = AppBackgroundWhite,
    surface = AppBackgroundWhite,
    surfaceContainerLow = AppSurfaceLow,
    surfaceVariant = AppSurfaceVariant,
    onPrimary = AppBackgroundWhite,
    onSecondary = AppBackgroundWhite,
    onTertiary = AppBackgroundWhite,
    onBackground = AppTextPrimary,
    onSurface = AppTextPrimary,
    onSurfaceVariant = AppTextSecondary,
)

@Composable
fun NotePassingAppTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = FixedColorScheme,
        typography = Typography,
        content = content
    )
}