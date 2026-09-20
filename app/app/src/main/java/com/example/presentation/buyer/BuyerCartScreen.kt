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
import com.example.data.remote.dto.CartItemDto

@Composable
fun BuyerCartScreen(
    viewModel: BuyerViewModel,
    onCheckoutSuccess: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(Unit) {
        viewModel.loadCart()
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
                val wasPaid = uiState.paymentSuccessOrder != null
                viewModel.dismissPayment()
                if (wasPaid) {
                    onCheckoutSuccess()
                }
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
            if (uiState.isLoadingCart && uiState.cart.items.isEmpty()) {
                LoadingView(message = "Loading your cart...")
            } else if (uiState.cart.items.isEmpty()) {
                EmptyView(
                    title = "Your Cart is Empty",
                    message = "Browse the marketplace to select pure, verified honey jars.",
                    icon = Icons.Default.ShoppingCart,
                    actionLabel = "Refresh Cart",
                    onAction = { viewModel.loadCart() }
                )
            } else {
                LazyColumn(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(uiState.cart.items, key = { it.productId }) { item ->
                        CartItemRow(
                            item = item,
                            onRemove = { viewModel.removeFromCart(item.productId) }
                        )
                    }
                }

                // Checkout Summary Bar
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = "Total Items",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                text = "${uiState.cart.totalItems}",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold
                            )
                        }

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = "Total Price",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "₹${uiState.cart.totalPrice.toInt()}",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }

                        if (uiState.checkoutError != null) {
                            Text(
                                text = uiState.checkoutError.orEmpty(),
                                color = MaterialTheme.colorScheme.error,
                                style = MaterialTheme.typography.bodySmall
                            )
                        }

                        HoneyButton(
                            text = "Checkout & Pay Now",
                            onClick = {
                                viewModel.checkout { orderId ->
                                    val order = viewModel.uiState.value.checkoutSuccessOrder
                                    if (order != null) {
                                        viewModel.startPayment(order)
                                    }
                                }
                            },
                            isLoading = uiState.isCheckingOut,
                            icon = Icons.Default.Payment,
                            testTag = "cart_checkout_button"
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun CartItemRow(
    item: CartItemDto,
    onRemove: () -> Unit
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = RoundedCornerShape(10.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = item.title,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "${item.jarSizeGrams}g Jar • Qty: ${item.quantity}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = "₹${item.subtotal.toInt()} (₹${item.unitPrice.toInt()} each)",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            IconButton(
                onClick = onRemove,
                modifier = Modifier.testTag("remove_item_${item.productId}")
            ) {
                Icon(
                    imageVector = Icons.Default.DeleteOutline,
                    contentDescription = "Remove item",
                    tint = MaterialTheme.colorScheme.error
                )
            }
        }
    }
}
