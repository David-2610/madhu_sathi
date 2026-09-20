package com.example.presentation.admin

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.core.network.WebSocketState
import com.example.core.ui.*
import com.example.data.local.entity.UserProfileEntity
import com.example.data.remote.dto.*
import com.example.presentation.trace.QrTraceScannerScreen
import com.example.presentation.trace.TraceViewModel

@Composable
fun AdminShellScreen(
    adminViewModel: AdminViewModel,
    traceViewModel: TraceViewModel,
    userProfile: UserProfileEntity?,
    onLogout: () -> Unit
) {
    var selectedTab by remember { mutableIntStateOf(0) }
    val uiState by adminViewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            Column {
                HoneyTopAppBar(
                    title = when (selectedTab) {
                        0 -> "KVIC Quality Dashboard"
                        1 -> "Verify Digital Passports"
                        else -> "Admin Settings"
                    },
                    subtitle = "Real-time AI monitoring & compliance",
                    actions = {
                        IconButton(onClick = { adminViewModel.loadDashboardData() }) {
                            Icon(Icons.Default.Refresh, contentDescription = "Refresh Data")
                        }
                    }
                )
                // Connection State Banner
                if (uiState.connectionState != WebSocketState.CONNECTED) {
                    val bgColor = if (uiState.connectionState == WebSocketState.RECONNECTING) 
                                     MaterialTheme.colorScheme.errorContainer 
                                  else MaterialTheme.colorScheme.surfaceVariant
                    val txtColor = if (uiState.connectionState == WebSocketState.RECONNECTING) 
                                      MaterialTheme.colorScheme.onErrorContainer 
                                   else MaterialTheme.colorScheme.onSurfaceVariant
                    
                    Box(modifier = Modifier.fillMaxWidth().background(bgColor).padding(4.dp), contentAlignment = Alignment.Center) {
                        Text(
                            text = "Status: ${uiState.connectionState.name}",
                            style = MaterialTheme.typography.labelSmall,
                            color = txtColor
                        )
                    }
                }
            }
        },
        bottomBar = {
            NavigationBar(modifier = Modifier.testTag("admin_bottom_bar")) {
                NavigationBarItem(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    icon = { Icon(Icons.Default.Dashboard, contentDescription = "Dashboard") },
                    label = { Text("Dashboard") }
                )
                NavigationBarItem(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    icon = { Icon(Icons.Default.QrCodeScanner, contentDescription = "Trace") },
                    label = { Text("Inspect Trace") }
                )
                NavigationBarItem(
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 },
                    icon = { Icon(Icons.Default.AdminPanelSettings, contentDescription = "Settings") },
                    label = { Text("Admin") }
                )
            }
        }
    ) { padding ->
        Surface(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            when (selectedTab) {
                0 -> AdminKvicDashboardView(
                    uiState = uiState,
                    onRefresh = { adminViewModel.loadDashboardData() }
                )
                1 -> QrTraceScannerScreen(viewModel = traceViewModel, canNavigateBack = false)
                2 -> AdminSettingsView(
                    userProfile = userProfile,
                    onLogout = onLogout
                )
            }
        }
    }
}

@Composable
private fun AdminKvicDashboardView(
    uiState: AdminUiState,
    onRefresh: () -> Unit
) {
    if (uiState.isLoading && uiState.overview == null) {
        LoadingView(message = "Connecting to KVIC Node...")
        return
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        contentPadding = PaddingValues(bottom = 24.dp)
    ) {
        // Overview Stats
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "National Overview",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                IconButton(onClick = onRefresh) {
                    Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                }
            }
            Spacer(modifier = Modifier.height(8.dp))
            
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                StatCard(
                    title = "Total Hives",
                    value = "${uiState.overview?.totalHives ?: 0}",
                    icon = Icons.Default.AllInclusive,
                    modifier = Modifier.weight(1f)
                )
                StatCard(
                    title = "Healthy",
                    value = "${uiState.overview?.healthy ?: 0}",
                    icon = Icons.Default.CheckCircle,
                    modifier = Modifier.weight(1f)
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                StatCard(
                    title = "Warning",
                    value = "${uiState.overview?.warning ?: 0}",
                    icon = Icons.Default.Warning,
                    modifier = Modifier.weight(1f)
                )
                StatCard(
                    title = "Critical",
                    value = "${uiState.overview?.critical ?: 0}",
                    icon = Icons.Default.Error,
                    modifier = Modifier.weight(1f)
                )
            }
        }

        // Live Alerts Feed
        item {
            Text(
                text = "Live Alert Stream",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.error
            )
        }
        if (uiState.alerts.isEmpty()) {
            item {
                Text("No active alerts.", style = MaterialTheme.typography.bodySmall)
            }
        } else {
            items(uiState.alerts.take(5), key = { it.alertId }) { alert ->
                KvicAlertItem(alert)
            }
        }

        // Hive List with AI
        item {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "Active Hives AI Analysis",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
        }
        items(uiState.hives, key = { it.hiveId }) { hive ->
            KvicHiveItem(hive)
        }
    }
}

@Composable
private fun KvicAlertItem(alert: KvicAlertDto) {
    val bgColor = if (alert.severity == "CRITICAL") MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.surfaceVariant
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = bgColor),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(text = "Hive: ${alert.hiveId}", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelSmall)
                Text(text = alert.severity, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.error)
            }
            Text(text = alert.message, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(top = 4.dp))
        }
    }
}

@Composable
private fun KvicHiveItem(hive: KvicHiveDto) {
    val isHighRisk = hive.status == "CRITICAL"
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (isHighRisk) MaterialTheme.colorScheme.errorContainer.copy(alpha=0.2f) else MaterialTheme.colorScheme.surface
        ),
        shape = RoundedCornerShape(10.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Hive ID: ${hive.hiveId}", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleSmall)
                StatusBadge(status = hive.status)
            }
            
            if (hive.aiSummary != null) {
                Text(
                    text = "AI INSIGHT",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = hive.aiSummary.conditionSummary,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = hive.aiSummary.explanation,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                if (hive.aiSummary.recommendedSteps.isNotEmpty()) {
                    Text(
                        text = "Action: ${hive.aiSummary.recommendedSteps.first()}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.error
                    )
                }
            } else {
                Text(
                    text = "Awaiting AI Analysis...",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun AdminSettingsView(
    userProfile: UserProfileEntity?,
    onLogout: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(
                    text = userProfile?.fullName ?: "KVIC Quality Enforcement Officer",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = userProfile?.email ?: "admin@kvic.gov.in",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                StatusBadge(status = "KVIC_ADMIN")
            }
        }

        Button(
            onClick = onLogout,
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp)
                .testTag("admin_logout_button"),
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.errorContainer,
                contentColor = MaterialTheme.colorScheme.onErrorContainer
            ),
            shape = RoundedCornerShape(10.dp)
        ) {
            Icon(Icons.Default.Logout, contentDescription = null, modifier = Modifier.size(18.dp))
            Spacer(modifier = Modifier.width(8.dp))
            Text("Sign Out", fontWeight = FontWeight.SemiBold)
        }
    }
}
