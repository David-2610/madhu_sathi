package com.example.presentation.beekeeper

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import com.example.core.ui.HoneyTopAppBar
import com.example.data.local.entity.UserProfileEntity

@Composable
fun BeekeeperShellScreen(
    viewModel: BeekeeperViewModel,
    userProfile: UserProfileEntity?,
    onLogout: () -> Unit
) {
    var selectedTab by remember { mutableIntStateOf(0) }
    var apiarySubTab by remember { mutableIntStateOf(0) } // 0: Apiaries, 1: Hives

    val uiState by viewModel.uiState.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(uiState.successMessage) {
        uiState.successMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearMessages()
        }
    }
    LaunchedEffect(uiState.errorMessage) {
        uiState.errorMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearMessages()
        }
    }

    val tabs = listOf(
        Triple("Dashboard", Icons.Default.Dashboard, 0),
        Triple("Apiaries", Icons.Default.Terrain, 1),
        Triple("Honey", Icons.Default.WaterDrop, 2),
        Triple("IoT & Alerts", Icons.Default.Sensors, 3),
        Triple("AI & Guides", Icons.Default.Psychology, 4),
        Triple("Profile", Icons.Default.Person, 5)
    )

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            HoneyTopAppBar(
                title = when (selectedTab) {
                    0 -> "Beekeeper Dashboard"
                    1 -> if (apiarySubTab == 0) "Apiary Locations" else "Hives & Colonies"
                    2 -> "Harvests & Digital Passports"
                    3 -> "IoT Colony Telemetry"
                    4 -> "AI & Learning Academy"
                    else -> "Beekeeper Profile"
                },
                subtitle = "Rural-Tech Smart Beekeeping",
                canNavigateBack = (selectedTab == 1 && apiarySubTab == 1),
                onNavigateBack = {
                    if (selectedTab == 1 && apiarySubTab == 1) {
                        apiarySubTab = 0
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.refreshData() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh Data")
                    }
                }
            )
        },
        bottomBar = {
            NavigationBar(modifier = Modifier.testTag("beekeeper_bottom_bar")) {
                tabs.forEach { (label, icon, index) ->
                    val isSelected = selectedTab == index
                    NavigationBarItem(
                        selected = isSelected,
                        onClick = { 
                            selectedTab = index 
                            // Reset sub-tabs when switching main tabs to start from the root of each section
                            if (index == 1) apiarySubTab = 0
                        },
                        icon = {
                            if (index == 3 && uiState.alerts.any { !it.isResolved }) {
                                BadgedBox(badge = {
                                    Badge { Text("${uiState.alerts.count { !it.isResolved }}") }
                                }) {
                                    Icon(icon, contentDescription = label)
                                }
                            } else {
                                Icon(icon, contentDescription = label)
                            }
                        },
                        label = { Text(label) },
                        modifier = Modifier.testTag("beekeeper_nav_$index")
                    )
                }
            }
        }
    ) { padding ->
        Surface(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            when (selectedTab) {
                0 -> BeekeeperDashboardScreen(
                    viewModel = viewModel,
                    onNavigateToApiaries = {
                        selectedTab = 1
                        apiarySubTab = 0
                    },
                    onNavigateToHoney = { selectedTab = 2 },
                    onNavigateToIoT = { selectedTab = 3 },
                    onNavigateToAssistant = {
                        selectedTab = 4
                    }
                )
                1 -> {
                    if (apiarySubTab == 0) {
                        BeekeeperApiariesScreen(
                            viewModel = viewModel,
                            onApiarySelected = { apiarySubTab = 1 }
                        )
                    } else {
                        BeekeeperHivesScreen(
                            viewModel = viewModel,
                            onHiveSelected = { selectedTab = 3 } // Quick jump to IoT on hive select
                        )
                    }
                }
                2 -> BeekeeperHoneyScreen(viewModel = viewModel)
                3 -> BeekeeperIoTScreen(viewModel = viewModel)
                4 -> BeekeeperLearningScreen(viewModel = viewModel)
                5 -> BeekeeperProfileScreen(
                    viewModel = viewModel,
                    userProfile = userProfile,
                    onLogout = onLogout
                )
            }
        }
    }
}
