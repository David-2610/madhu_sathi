package com.example.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

private val DarkColorScheme =
  darkColorScheme(
    primary = Color(0xFFFBBF24),
    onPrimary = Color(0xFF451A03),
    primaryContainer = HoneyOnGoldContainer,
    onPrimaryContainer = HoneyGoldContainer,
    secondary = Color(0xFF34D399),
    onSecondary = Color(0xFF022C22),
    secondaryContainer = ForestOnGreenContainer,
    onSecondaryContainer = ForestGreenContainer,
    tertiary = Color(0xFF38BDF8),
    background = HoneyBgDark,
    surface = HoneySurfaceDark,
    surfaceVariant = HoneySurfaceVariantDark,
    outline = HoneyOutlineDark
  )

private val LightColorScheme =
  lightColorScheme(
    primary = HoneyGoldPrimary,
    onPrimary = Color.White,
    primaryContainer = HoneyGoldContainer,
    onPrimaryContainer = HoneyOnGoldContainer,
    secondary = ForestGreenSecondary,
    onSecondary = Color.White,
    secondaryContainer = ForestGreenContainer,
    onSecondaryContainer = ForestOnGreenContainer,
    tertiary = TraceBlueTertiary,
    onTertiary = Color.White,
    tertiaryContainer = TraceBlueContainer,
    onTertiaryContainer = TraceOnBlueContainer,
    background = HoneyBgLight,
    surface = HoneySurfaceLight,
    surfaceVariant = HoneySurfaceVariantLight,
    outline = HoneyOutlineLight
  )

@Composable
fun MyApplicationTheme(
  darkTheme: Boolean = isSystemInDarkTheme(),
  // Dynamic color disabled to ensure the custom HoneyChain theme renders immediately
  // and avoid a black screen flash on startup.
  dynamicColor: Boolean = false,
  content: @Composable () -> Unit,
) {
  val colorScheme =
    when {
      dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
        val context = LocalContext.current
        if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
      }

      darkTheme -> DarkColorScheme
      else -> LightColorScheme
    }

  MaterialTheme(colorScheme = colorScheme, typography = Typography, content = content)
}
