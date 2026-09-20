package com.example.presentation.buyer

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
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
import com.example.data.remote.dto.OrderDto

@Composable
fun BuyerOrdersScreen(
    viewModel: BuyerViewModel
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(Unit) {
        viewModel.loadOrders()
    }

    if (uiState.activePaymentOrder != null) {
        MockPaymentDialog(
            order = uiState.activePaymentOrder!!,
            isProcessing = uiState.isProcessingPayment,
            successOrder = uiState.paymentSuccessOrder,
            errorMessage = uiState.paymentError,
            onConfirmPayment = { mockSuccess, methodTitle ->
                viewModel.confirmPayment(
                    orderId = uiState.activePaymentOrder!!.id,
                    mockSuccess = mockSuccess,
                    methodLabel = methodTitle
                )
            },
            onDismiss = {
                viewModel.dismissPayment()
            }
        )
    }

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Order History (${uiState.orders.size})",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                FilledTonalButton(
                    onClick = { viewModel.loadOrders() },
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.testTag("refresh_orders_button")
                ) {
                    Icon(Icons.Default.Refresh, contentDescription = "Refresh", modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Refresh", style = MaterialTheme.typography.labelSmall)
                }
            }

            if (uiState.isLoadingOrders && uiState.orders.isEmpty()) {
                LoadingView(message = "Loading your orders...")
            } else if (uiState.ordersError != null && uiState.orders.isEmpty()) {
                ErrorCard(
                    message = uiState.ordersError.orEmpty(),
                    onRetry = { viewModel.loadOrders() }
                )
            } else if (uiState.orders.isEmpty()) {
                EmptyView(
                    title = "No Orders Yet",
                    message = "Your completed purchases and delivery tracking will appear here.",
                    icon = Icons.Default.ReceiptLong,
                    actionLabel = "Refresh Orders",
                    onAction = { viewModel.loadOrders() }
                )
            } else {
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(bottom = 24.dp)
                ) {
                    items(uiState.orders, key = { it.id }) { order ->
                        OrderItemCard(
                            order = order,
                            onPayNow = {
                                viewModel.startPayment(order)
                            }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun OrderItemCard(
    order: OrderDto,
    onPayNow: () -> Unit
) {
    val isPaid = order.paymentStatus == "PAID" || order.status == "PAID" || order.paymentStatus == "COMPLETED"

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .testTag("order_card_${order.id}"),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = RoundedCornerShape(12.dp)
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
                Column {
                    Text(
                        text = "Order #${order.displayOrderCode}",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold
                    )
                    if (!order.createdAt.isNullOrBlank()) {
                        Text(
                            text = order.createdAt.take(10),
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                StatusBadge(status = order.status)
            }

            HorizontalDivider()

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "Items Count: ${order.items.size}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = "Payment: ${order.paymentStatus}",
                    style = MaterialTheme.typography.bodySmall,
                    fontWeight = FontWeight.SemiBold,
                    color = if (isPaid)
                        MaterialTheme.colorScheme.primary
                    else
                        MaterialTheme.colorScheme.error
                )
            }

            // List item titles
            order.items.forEach { item ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "• ${item.title} (x${item.quantity})",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.weight(1f)
                    )
                    Text(
                        text = "₹${item.subtotal.toInt()}",
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Total Amount",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "₹${order.totalAmount.toInt()}",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            if (order.latestPayment != null && isPaid) {
                Surface(
                    color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                    shape = RoundedCornerShape(6.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Ref: ${order.latestPayment.paymentReference}",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = order.latestPayment.provider,
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }

            if (!isPaid) {
                Button(
                    onClick = onPayNow,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(40.dp)
                        .testTag("pay_order_${order.id}"),
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Icon(Icons.Default.CreditCard, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Pay Now ₹${order.totalAmount.toInt()} (Mock Payment Gateway)", style = MaterialTheme.typography.labelMedium)
                }
            }
        }
    }
}
