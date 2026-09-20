package com.example.presentation.buyer

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
import com.example.presentation.trace.QrTraceScannerScreen
import com.example.presentation.trace.TraceViewModel

@Composable
fun BuyerShellScreen(
    buyerViewModel: BuyerViewModel,
    traceViewModel: TraceViewModel,
    userProfile: UserProfileEntity?,
    onLogout: () -> Unit
) {
    var selectedTab by remember { mutableIntStateOf(0) }
    val buyerUiState by buyerViewModel.uiState.collectAsState()

    val tabs = listOf(
        Triple("Marketplace", Icons.Default.Storefront, 0),
        Triple("Orders", Icons.Default.ReceiptLong, 1),
        Triple("Cart", Icons.Default.ShoppingCart, 2),
        Triple("QR Trace", Icons.Default.QrCodeScanner, 3),
        Triple("Profile", Icons.Default.Person, 4)
    )

    Scaffold(
        topBar = {
            HoneyTopAppBar(
                title = when (selectedTab) {
                    0 -> "Honey Marketplace"
                    1 -> "My Orders"
                    2 -> "Shopping Cart"
                    3 -> "Verify Traceability"
                    else -> "Buyer Profile"
                },
                subtitle = "Pure Khadi Honey Direct From Apiaries",
                actions = {
                    if (selectedTab == 0) {
                        IconButton(
                            onClick = { buyerViewModel.loadMarketplace() },
                            modifier = Modifier.testTag("topbar_refresh_marketplace")
                        ) {
                            Icon(Icons.Default.Refresh, contentDescription = "Refresh Marketplace")
                        }
                    } else if (selectedTab == 1) {
                        IconButton(
                            onClick = { buyerViewModel.loadOrders() },
                            modifier = Modifier.testTag("topbar_refresh_orders")
                        ) {
                            Icon(Icons.Default.Refresh, contentDescription = "Refresh Orders")
                        }
                    }
                }
            )
        },
        bottomBar = {
            NavigationBar(
                modifier = Modifier.testTag("buyer_bottom_bar")
            ) {
                tabs.forEach { (label, icon, index) ->
                    val isSelected = selectedTab == index
                    NavigationBarItem(
                        selected = isSelected,
                        onClick = {
                            selectedTab = index
                            when (index) {
                                0 -> buyerViewModel.loadMarketplace()
                                1 -> buyerViewModel.loadOrders()
                                2 -> buyerViewModel.loadCart()
                            }
                        },
                        icon = {
                            if (index == 2 && buyerUiState.cart.totalItems > 0) {
                                BadgedBox(badge = {
                                    Badge { Text("${buyerUiState.cart.totalItems}") }
                                }) {
                                    Icon(icon, contentDescription = label)
                                }
                            } else {
                                Icon(icon, contentDescription = label)
                            }
                        },
                        label = { Text(label) },
                        modifier = Modifier.testTag("buyer_nav_$index")
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
                0 -> BuyerHomeScreen(
                    viewModel = buyerViewModel,
                    onNavigateToTrace = { token ->
                        traceViewModel.searchTrace(token)
                        selectedTab = 3
                    }
                )
                1 -> BuyerOrdersScreen(viewModel = buyerViewModel)
                2 -> BuyerCartScreen(
                    viewModel = buyerViewModel,
                    onCheckoutSuccess = { selectedTab = 1 }
                )
                3 -> QrTraceScannerScreen(
                    viewModel = traceViewModel,
                    canNavigateBack = false
                )
                4 -> BuyerProfileScreen(
                    userProfile = userProfile,
                    onLogout = onLogout
                )
            }
        }
    }
}
