package com.example.presentation.admin

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
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.core.ui.*
import com.example.data.local.entity.UserProfileEntity
import com.example.data.remote.dto.ProductDto
import com.example.presentation.trace.QrTraceScannerScreen
import com.example.presentation.trace.TraceViewModel

@Composable
fun AdminShellScreen(
    adminViewModel: AdminViewModel,
    traceViewModel: TraceViewModel,
    userProfile: UserProfileEntity?,
    backendUrl: String,
    onOpenBackendConfig: () -> Unit,
    onLogout: () -> Unit
) {
    var selectedTab by remember { mutableIntStateOf(0) }
    val uiState by adminViewModel.uiState.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(uiState.successMessage) {
        uiState.successMessage?.let {
            snackbarHostState.showSnackbar(it)
            adminViewModel.clearMessages()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            HoneyTopAppBar(
                title = when (selectedTab) {
                    0 -> "KVIC Honey Audit Portal"
                    1 -> "Verify Digital Passports"
                    else -> "Admin Settings"
                },
                subtitle = "Khadi & Village Industries Commission Quality Enforcement",
                actions = {
                    IconButton(onClick = onOpenBackendConfig) {
                        Icon(Icons.Default.Dns, contentDescription = "Configure Backend")
                    }
                }
            )
        },
        bottomBar = {
            NavigationBar(modifier = Modifier.testTag("admin_bottom_bar")) {
                NavigationBarItem(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    icon = { Icon(Icons.Default.VerifiedUser, contentDescription = "Audits") },
                    label = { Text("Quality Audits") }
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
                0 -> AdminAuditView(
                    uiState = uiState,
                    onUpdateStatus = { id, status -> adminViewModel.updateProductStatus(id, status) },
                    onInspectTrace = { token ->
                        traceViewModel.searchTrace(token)
                        selectedTab = 1
                    },
                    onRefresh = { adminViewModel.loadAudits() }
                )
                1 -> QrTraceScannerScreen(viewModel = traceViewModel, canNavigateBack = false)
                2 -> AdminSettingsView(
                    userProfile = userProfile,
                    backendUrl = backendUrl,
                    healthStatus = uiState.healthCheck?.status ?: "Unknown",
                    onOpenBackendConfig = onOpenBackendConfig,
                    onLogout = onLogout
                )
            }
        }
    }
}

@Composable
private fun AdminAuditView(
    uiState: AdminUiState,
    onUpdateStatus: (String, String) -> Unit,
    onInspectTrace: (String) -> Unit,
    onRefresh: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Summary Metrics
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            StatCard(
                title = "Audited Jars",
                value = "${uiState.products.size}",
                icon = Icons.Default.Inventory2,
                modifier = Modifier.weight(1f)
            )
            StatCard(
                title = "Backend Service",
                value = uiState.healthCheck?.status?.uppercase() ?: "ONLINE",
                icon = Icons.Default.Dns,
                modifier = Modifier.weight(1f)
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Marketplace Honey Jars Under Audit",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold
            )
            IconButton(onClick = onRefresh) {
                Icon(Icons.Default.Refresh, contentDescription = "Refresh")
            }
        }

        if (uiState.isLoading && uiState.products.isEmpty()) {
            LoadingView(message = "Fetching audit catalog...")
        } else if (uiState.products.isEmpty()) {
            EmptyView(
                title = "No Honey Products Listed",
                message = "Products bottled and listed by beekeepers will be queued here for KVIC compliance check.",
                icon = Icons.Default.Shield
            )
        } else {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(12.dp),
                contentPadding = PaddingValues(bottom = 24.dp)
            ) {
                items(uiState.products, key = { it.id }) { product ->
                    AdminProductAuditCard(
                        product = product,
                        onUpdateStatus = onUpdateStatus,
                        onInspectTrace = onInspectTrace
                    )
                }
            }
        }
    }
}

@Composable
private fun AdminProductAuditCard(
    product: ProductDto,
    onUpdateStatus: (String, String) -> Unit,
    onInspectTrace: (String) -> Unit
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = product.title,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold
                )
                StatusBadge(status = product.status)
            }

            Text(
                text = "Token: ${product.traceToken} • Size: ${product.jarSizeGrams}g • Listed: ${if (product.isListed) "Yes" else "No"}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedButton(
                    onClick = { onInspectTrace(product.traceToken) },
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(Icons.Default.QrCode, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Audit Chain")
                }

                if (product.status != "VERIFIED") {
                    Button(
                        onClick = { onUpdateStatus(product.id, "VERIFIED") },
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Approve")
                    }
                } else {
                    OutlinedButton(
                        onClick = { onUpdateStatus(product.id, "SUSPICIOUS") },
                        shape = RoundedCornerShape(8.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Flag")
                    }
                }
            }
        }
    }
}

@Composable
private fun AdminSettingsView(
    userProfile: UserProfileEntity?,
    backendUrl: String,
    healthStatus: String,
    onOpenBackendConfig: () -> Unit,
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

        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(text = "Server & Infrastructure", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                OutlinedButton(
                    onClick = onOpenBackendConfig,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Icon(Icons.Default.Dns, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Base URL: ${backendUrl.removePrefix("http://")}")
                }
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
