package com.example.presentation.buyer

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.example.data.remote.dto.OrderDto

enum class MockPaymentMethod(
    val id: String,
    val title: String,
    val subtitle: String,
    val icon: ImageVector
) {
    UPI("UPI", "UPI / QR Code", "Google Pay, PhonePe, Paytm, BHIM", Icons.Default.QrCode2),
    CARD("CARD", "Cards", "Debit, Credit & ATM Cards", Icons.Default.CreditCard),
    NETBANKING("NETBANKING", "Net Banking", "SBI, HDFC, ICICI, Axis Bank", Icons.Default.AccountBalance),
    COD("COD", "Cash on Delivery", "Pay cash upon authentic jar delivery", Icons.Default.LocalShipping)
}

@Composable
fun MockPaymentDialog(
    order: OrderDto,
    isProcessing: Boolean,
    successOrder: OrderDto?,
    errorMessage: String?,
    onConfirmPayment: (mockSuccess: Boolean, methodTitle: String) -> Unit,
    onDismiss: () -> Unit
) {
    var selectedMethod by remember { mutableStateOf(MockPaymentMethod.UPI) }
    var selectedUpiApp by remember { mutableStateOf("Google Pay") }
    var customUpiId by remember { mutableStateOf("buyer@oksbi") }
    var cardNumber by remember { mutableStateOf("4532 •••• •••• 8921") }
    var cardExpiry by remember { mutableStateOf("08/28") }
    var cardCvv by remember { mutableStateOf("542") }
    var selectedBank by remember { mutableStateOf("State Bank of India") }
    var simulateSuccess by remember { mutableStateOf(true) }

    Dialog(
        onDismissRequest = {
            if (!isProcessing) onDismiss()
        },
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Card(
            modifier = Modifier
                .fillMaxWidth(0.94f)
                .fillMaxHeight(0.88f)
                .testTag("mock_payment_dialog"),
            shape = RoundedCornerShape(20.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(20.dp)
            ) {
                // Top header bar
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Surface(
                            shape = CircleShape,
                            color = MaterialTheme.colorScheme.primaryContainer,
                            modifier = Modifier.size(36.dp)
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Icon(
                                    imageVector = Icons.Default.Security,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                        }
                        Column {
                            Text(
                                text = "MadhuSathi Pay",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "256-bit Encrypted Mock Gateway",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }

                    if (!isProcessing) {
                        IconButton(
                            onClick = onDismiss,
                            modifier = Modifier.testTag("close_payment_dialog")
                        ) {
                            Icon(Icons.Default.Close, contentDescription = "Close")
                        }
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))
                HorizontalDivider()
                Spacer(modifier = Modifier.height(12.dp))

                AnimatedContent(
                    targetState = when {
                        successOrder != null -> PaymentScreenStage.SUCCESS
                        isProcessing -> PaymentScreenStage.PROCESSING
                        else -> PaymentScreenStage.FORM
                    },
                    transitionSpec = { fadeIn() togetherWith fadeOut() },
                    label = "payment_stage"
                ) { stage ->
                    when (stage) {
                        PaymentScreenStage.FORM -> {
                            PaymentFormView(
                                order = order,
                                selectedMethod = selectedMethod,
                                onSelectMethod = { selectedMethod = it },
                                selectedUpiApp = selectedUpiApp,
                                onSelectUpiApp = { selectedUpiApp = it },
                                customUpiId = customUpiId,
                                onCustomUpiIdChange = { customUpiId = it },
                                cardNumber = cardNumber,
                                onCardNumberChange = { cardNumber = it },
                                cardExpiry = cardExpiry,
                                onCardExpiryChange = { cardExpiry = it },
                                cardCvv = cardCvv,
                                onCardCvvChange = { cardCvv = it },
                                selectedBank = selectedBank,
                                onSelectBank = { selectedBank = it },
                                simulateSuccess = simulateSuccess,
                                onToggleSimulateSuccess = { simulateSuccess = it },
                                errorMessage = errorMessage,
                                onPayClicked = {
                                    val methodLabel = when (selectedMethod) {
                                        MockPaymentMethod.UPI -> "UPI ($selectedUpiApp)"
                                        MockPaymentMethod.CARD -> "Card (${cardNumber.takeLast(4)})"
                                        MockPaymentMethod.NETBANKING -> "Net Banking ($selectedBank)"
                                        MockPaymentMethod.COD -> "Cash on Delivery"
                                    }
                                    onConfirmPayment(simulateSuccess, methodLabel)
                                }
                            )
                        }
                        PaymentScreenStage.PROCESSING -> {
                            PaymentProcessingView(order = order)
                        }
                        PaymentScreenStage.SUCCESS -> {
                            PaymentSuccessReceiptView(
                                order = successOrder ?: order,
                                onDone = onDismiss
                            )
                        }
                    }
                }
            }
        }
    }
}

private enum class PaymentScreenStage {
    FORM,
    PROCESSING,
    SUCCESS
}

@Composable
private fun PaymentFormView(
    order: OrderDto,
    selectedMethod: MockPaymentMethod,
    onSelectMethod: (MockPaymentMethod) -> Unit,
    selectedUpiApp: String,
    onSelectUpiApp: (String) -> Unit,
    customUpiId: String,
    onCustomUpiIdChange: (String) -> Unit,
    cardNumber: String,
    onCardNumberChange: (String) -> Unit,
    cardExpiry: String,
    onCardExpiryChange: (String) -> Unit,
    cardCvv: String,
    onCardCvvChange: (String) -> Unit,
    selectedBank: String,
    onSelectBank: (String) -> Unit,
    simulateSuccess: Boolean,
    onToggleSimulateSuccess: (Boolean) -> Unit,
    errorMessage: String?,
    onPayClicked: () -> Unit
) {
    val scrollState = rememberScrollState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scrollState),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        // Order Summary Card
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)),
            shape = RoundedCornerShape(12.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Order #${order.displayOrderCode}",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Total Payable",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "${order.items.size} verified honey unit(s)",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = "₹${order.totalAmount.toInt()}",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.ExtraBold,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
        }

        // Select Payment Method Header
        Text(
            text = "Select Payment Method",
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.Bold
        )

        // Method selector grid / cards
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            MockPaymentMethod.values().forEach { method ->
                val isSelected = selectedMethod == method
                Surface(
                    modifier = Modifier
                        .weight(1f)
                        .height(72.dp)
                        .clip(RoundedCornerShape(10.dp))
                        .clickable { onSelectMethod(method) }
                        .testTag("payment_method_${method.id}"),
                    color = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f),
                    border = BorderStroke(
                        width = if (isSelected) 1.5.dp else 0.5.dp,
                        color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant
                    ),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(6.dp),
                        verticalArrangement = Arrangement.Center,
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(
                            imageVector = method.icon,
                            contentDescription = method.title,
                            tint = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.size(22.dp)
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = method.title,
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                            color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,
                            fontSize = 11.sp
                        )
                    }
                }
            }
        }

        // Method Details Input Box
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.25f)),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(14.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                when (selectedMethod) {
                    MockPaymentMethod.UPI -> {
                        Text(
                            text = "Choose UPI Application or VPA",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.SemiBold
                        )
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            listOf("Google Pay", "PhonePe", "Paytm", "BHIM").forEach { app ->
                                val isAppSelected = selectedUpiApp == app
                                FilterChip(
                                    selected = isAppSelected,
                                    onClick = { onSelectUpiApp(app) },
                                    label = { Text(app, style = MaterialTheme.typography.labelSmall) },
                                    modifier = Modifier.testTag("upi_app_$app")
                                )
                            }
                        }

                        OutlinedTextField(
                            value = customUpiId,
                            onValueChange = onCustomUpiIdChange,
                            label = { Text("UPI ID / Virtual Payment Address") },
                            placeholder = { Text("e.g. mobile@upi") },
                            modifier = Modifier
                                .fillMaxWidth()
                                .testTag("upi_id_input"),
                            singleLine = true,
                            leadingIcon = { Icon(Icons.Default.AlternateEmail, contentDescription = null) },
                            trailingIcon = {
                                Icon(Icons.Default.CheckCircle, contentDescription = "Verified", tint = MaterialTheme.colorScheme.primary)
                            }
                        )
                    }

                    MockPaymentMethod.CARD -> {
                        Text(
                            text = "Card Details (Simulation)",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.SemiBold
                        )
                        OutlinedTextField(
                            value = cardNumber,
                            onValueChange = onCardNumberChange,
                            label = { Text("Card Number") },
                            modifier = Modifier
                                .fillMaxWidth()
                                .testTag("card_number_input"),
                            singleLine = true,
                            leadingIcon = { Icon(Icons.Default.CreditCard, contentDescription = null) },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                        )
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            OutlinedTextField(
                                value = cardExpiry,
                                onValueChange = onCardExpiryChange,
                                label = { Text("Valid Thru") },
                                modifier = Modifier.weight(1f),
                                singleLine = true,
                                placeholder = { Text("MM/YY") }
                            )
                            OutlinedTextField(
                                value = cardCvv,
                                onValueChange = onCardCvvChange,
                                label = { Text("CVV") },
                                modifier = Modifier.weight(1f),
                                singleLine = true,
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                            )
                        }
                    }

                    MockPaymentMethod.NETBANKING -> {
                        Text(
                            text = "Select Indian Bank",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.SemiBold
                        )
                        listOf("State Bank of India", "HDFC Bank", "ICICI Bank", "Axis Bank").forEach { bank ->
                            val isBankSelected = selectedBank == bank
                            Surface(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(8.dp))
                                    .clickable { onSelectBank(bank) },
                                color = if (isBankSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface,
                                shape = RoundedCornerShape(8.dp)
                            ) {
                                Row(
                                    modifier = Modifier.padding(10.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text(
                                        text = bank,
                                        style = MaterialTheme.typography.bodyMedium,
                                        fontWeight = if (isBankSelected) FontWeight.Bold else FontWeight.Normal
                                    )
                                    RadioButton(
                                        selected = isBankSelected,
                                        onClick = { onSelectBank(bank) }
                                    )
                                }
                            }
                        }
                    }

                    MockPaymentMethod.COD -> {
                        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text(
                                text = "Cash on Delivery",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "Keep exact cash ready upon delivery. The courier will allow you to scan the tamper-proof jar QR code before payment.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }
        }

        // Simulation Sandbox Control
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer.copy(alpha = 0.4f)),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Science,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.tertiary,
                            modifier = Modifier.size(18.dp)
                        )
                        Text(
                            text = "Simulation Mode",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onTertiaryContainer
                        )
                    }

                    Switch(
                        checked = simulateSuccess,
                        onCheckedChange = onToggleSimulateSuccess,
                        modifier = Modifier.testTag("simulate_success_toggle")
                    )
                }

                Text(
                    text = if (simulateSuccess)
                        "Backend will approve payment, set Order to PAID, and mark product batch as SOLD."
                    else
                        "Backend will reject payment, set Order to PAYMENT_FAILED, and keep products ACTIVE.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onTertiaryContainer.copy(alpha = 0.9f)
                )
            }
        }

        if (errorMessage != null) {
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                shape = RoundedCornerShape(8.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(10.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.ErrorOutline,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.error
                    )
                    Text(
                        text = errorMessage,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onErrorContainer
                    )
                }
            }
        }

        Button(
            onClick = onPayClicked,
            modifier = Modifier
                .fillMaxWidth()
                .height(50.dp)
                .testTag("confirm_mock_payment_button"),
            shape = RoundedCornerShape(10.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = if (simulateSuccess) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
            )
        ) {
            Icon(Icons.Default.Lock, contentDescription = null, modifier = Modifier.size(18.dp))
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = if (simulateSuccess) "Pay ₹${order.totalAmount.toInt()} (Confirm)" else "Simulate Failed Payment",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@Composable
private fun PaymentProcessingView(order: OrderDto) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        CircularProgressIndicator(
            modifier = Modifier.size(54.dp),
            strokeWidth = 4.dp,
            color = MaterialTheme.colorScheme.primary
        )

        Spacer(modifier = Modifier.height(20.dp))

        Text(
            text = "Processing Secure Payment",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "Authorizing ₹${order.totalAmount.toInt()} with banking gateway & recording transaction...",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = androidx.compose.ui.text.style.TextAlign.Center
        )
    }
}

@Composable
private fun PaymentSuccessReceiptView(
    order: OrderDto,
    onDone: () -> Unit
) {
    val scrollState = rememberScrollState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(top = 8.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Surface(
            shape = CircleShape,
            color = MaterialTheme.colorScheme.primaryContainer,
            modifier = Modifier.size(68.dp)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.Default.CheckCircle,
                    contentDescription = "Success",
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(44.dp)
                )
            }
        }

        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = "Payment Confirmed!",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary
            )
            Text(
                text = "₹${order.totalAmount.toInt()} Paid Successfully",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
        }

        // Receipt Details Box
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)),
            shape = RoundedCornerShape(14.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                ReceiptRow(
                    label = "Order Number",
                    value = order.displayOrderCode
                )
                ReceiptRow(
                    label = "Payment Reference",
                    value = order.latestPayment?.paymentReference ?: "MOCK-PAY-${order.id}"
                )
                ReceiptRow(
                    label = "Gateway Provider",
                    value = order.latestPayment?.provider ?: "MOCK_GATEWAY"
                )
                ReceiptRow(
                    label = "Payment Status",
                    value = order.paymentStatus,
                    highlight = true
                )
                ReceiptRow(
                    label = "Backend Sync",
                    value = "Products marked SOLD"
                )
            }
        }

        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.4f)),
            shape = RoundedCornerShape(10.dp)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(12.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Verified,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.secondary
                )
                Text(
                    text = "Your digital honey certificates and verifiable passport batches have been registered.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSecondaryContainer
                )
            }
        }

        Spacer(modifier = Modifier.weight(1f, fill = false))

        Button(
            onClick = onDone,
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp)
                .testTag("payment_done_button"),
            shape = RoundedCornerShape(10.dp)
        ) {
            Text("Done & View My Orders", fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun ReceiptRow(
    label: String,
    value: String,
    highlight: Boolean = false
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodySmall,
            fontWeight = if (highlight) FontWeight.Bold else FontWeight.Medium,
            color = if (highlight) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
        )
    }
}
