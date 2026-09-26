package com.example.presentation.beekeeper

import androidx.compose.foundation.clickable
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import coil.compose.SubcomposeAsyncImage
import coil.request.ImageRequest
import com.example.BuildConfig
import com.example.core.ui.*
import com.example.data.remote.dto.*

@Composable
fun BeekeeperHoneyScreen(
    viewModel: BeekeeperViewModel
) {
    val uiState by viewModel.uiState.collectAsState()
    var selectedTab by remember { mutableIntStateOf(0) } // 0: Harvests, 1: Batches, 2: Products & Trace

    var showCreateHarvestDialog by remember { mutableStateOf(false) }
    var showCreateBatchDialog by remember { mutableStateOf(false) }
    var showCreateProductDialog by remember { mutableStateOf(false) }
    var showAddEventDialog by remember { mutableStateOf<String?>(null) }
    var showQrDialog by remember { mutableStateOf<ProductDto?>(null) }

    // Dialogs
    if (showCreateHarvestDialog && uiState.selectedHive != null) {
        CreateHarvestDialog(
            hiveCode = uiState.selectedHive!!.hiveCode,
            onDismiss = { showCreateHarvestDialog = false },
            onCreate = { date, qty, moisture, flora, notes ->
                viewModel.createHarvest(uiState.selectedHive!!.id, date, qty, moisture, flora, notes)
                showCreateHarvestDialog = false
            }
        )
    }

    if (showCreateBatchDialog && uiState.selectedHarvest != null) {
        CreateBatchDialog(
            maxHarvestQty = uiState.selectedHarvest!!.quantityKg,
            onDismiss = { showCreateBatchDialog = false },
            onCreate = { batchNum, totalKg, flora, grade ->
                viewModel.createBatch(uiState.selectedHarvest!!.id, batchNum, totalKg, flora, grade)
                showCreateBatchDialog = false
            }
        )
    }

    if (showCreateProductDialog && uiState.selectedBatch != null) {
        CreateProductDialog(
            batchNumber = uiState.selectedBatch!!.batchNumber,
            onDismiss = { showCreateProductDialog = false },
            onCreate = { title, desc, jarSize, price ->
                viewModel.createProduct(uiState.selectedBatch!!.id, title, desc, jarSize, price)
                showCreateProductDialog = false
            }
        )
    }

    if (showAddEventDialog != null) {
        AddEventDialog(
            productId = showAddEventDialog!!,
            onDismiss = { showAddEventDialog = null },
            onAdd = { type, title, desc, loc ->
                viewModel.addProductEvent(showAddEventDialog!!, type, title, desc, loc)
                showAddEventDialog = null
            }
        )
    }

    if (showQrDialog != null) {
        ProductQrDialog(
            product = showQrDialog!!,
            qrResponse = uiState.selectedProductQr,
            onDismiss = {
                showQrDialog = null
                viewModel.clearProductQr()
            }
        )
    }

    Scaffold(
        floatingActionButton = {
            when (selectedTab) {
                0 -> if (uiState.selectedHive != null) {
                    FloatingActionButton(
                        onClick = { showCreateHarvestDialog = true },
                        modifier = Modifier.testTag("add_harvest_fab")
                    ) {
                        Icon(Icons.Default.Add, contentDescription = "Log Harvest")
                    }
                }
                1 -> if (uiState.selectedHarvest != null) {
                    FloatingActionButton(
                        onClick = { showCreateBatchDialog = true },
                        modifier = Modifier.testTag("add_batch_fab")
                    ) {
                        Icon(Icons.Default.Add, contentDescription = "Create Batch")
                    }
                }
                2 -> if (uiState.selectedBatch != null) {
                    FloatingActionButton(
                        onClick = { showCreateProductDialog = true },
                        modifier = Modifier.testTag("add_product_fab")
                    ) {
                        Icon(Icons.Default.Add, contentDescription = "Package Product")
                    }
                }
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            TabRow(
                selectedTabIndex = selectedTab,
                containerColor = MaterialTheme.colorScheme.surfaceVariant,
                modifier = Modifier.clip(RoundedCornerShape(12.dp))
            ) {
                Tab(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    text = { Text("1. Harvests") }
                )
                Tab(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    text = { Text("2. Batches") }
                )
                Tab(
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 },
                    text = { Text("3. Products & Trace") }
                )
            }

            when (selectedTab) {
                0 -> HarvestsTab(
                    uiState = uiState,
                    onSelectHarvest = { harvest ->
                        viewModel.loadBatches(harvest.id)
                        selectedTab = 1
                    },
                    onRequestAdd = { showCreateHarvestDialog = true }
                )
                1 -> BatchesTab(
                    uiState = uiState,
                    onSelectBatch = { batch ->
                        viewModel.loadProductsForBatch(batch.id)
                        selectedTab = 2
                    },
                    onRequestAdd = { showCreateBatchDialog = true }
                )
                2 -> ProductsTab(
                    uiState = uiState,
                    onToggleListing = { prod, isListed, price ->
                        viewModel.toggleProductListing(prod.id, isListed, price)
                    },
                    onViewQr = { prod ->
                        showQrDialog = prod
                        viewModel.loadProductQr(prod.id)
                    },
                    onAddEvent = { prod ->
                        showAddEventDialog = prod.id
                    },
                    onRequestAdd = { showCreateProductDialog = true }
                )
            }
        }
    }
}

@Composable
private fun HarvestsTab(
    uiState: BeekeeperUiState,
    onSelectHarvest: (HarvestDto) -> Unit,
    onRequestAdd: () -> Unit
) {
    if (uiState.selectedHive == null) {
        EmptyView(
            title = "No Hive Selected",
            message = "Select an active hive from the Hives tab to log a seasonal harvest.",
            icon = Icons.Default.Hive
        )
    } else if (uiState.harvests.isEmpty()) {
        EmptyView(
            title = "No Harvests for Hive ${uiState.selectedHive.hiveCode}",
            message = "Record harvested honey weight in kg and lab moisture %.",
            icon = Icons.Default.WaterDrop,
            actionLabel = "Record Harvest",
            onAction = onRequestAdd
        )
    } else {
        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(12.dp),
            contentPadding = PaddingValues(bottom = 80.dp)
        ) {
            items(uiState.harvests, key = { it.id }) { harvest ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onSelectHarvest(harvest) },
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(
                                text = "Harvest Date: ${harvest.harvestDate}",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "🍯 Quantity: ${harvest.quantityKg} kg",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.primary
                            )
                            harvest.moisturePercentage?.let {
                                Text(
                                    text = "💧 Moisture: $it% (KVIC Compliant)",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                        Button(
                            onClick = { onSelectHarvest(harvest) },
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Text("Create Batch")
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun BatchesTab(
    uiState: BeekeeperUiState,
    onSelectBatch: (BatchDto) -> Unit,
    onRequestAdd: () -> Unit
) {
    if (uiState.selectedHarvest == null) {
        EmptyView(
            title = "No Harvest Selected",
            message = "Please pick a harvest from step 1 to group into certified batches.",
            icon = Icons.Default.WaterDrop
        )
    } else if (uiState.batches.isEmpty()) {
        EmptyView(
            title = "No Batches for this Harvest",
            message = "Create a processing batch from the ${uiState.selectedHarvest.quantityKg}kg harvest.",
            icon = Icons.Default.Layers,
            actionLabel = "Create Batch",
            onAction = onRequestAdd
        )
    } else {
        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(12.dp),
            contentPadding = PaddingValues(bottom = 80.dp)
        ) {
            items(uiState.batches, key = { it.id }) { batch ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onSelectBatch(batch) },
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(
                                text = "Batch #${batch.batchNumber}",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "Total: ${batch.totalQuantityKg} kg • Grade: ${batch.qualityGrade ?: "A"}",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.primary,
                                fontWeight = FontWeight.SemiBold
                            )
                            StatusBadge(status = batch.status)
                        }
                        Button(
                            onClick = { onSelectBatch(batch) },
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Text("Package Jars")
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ProductsTab(
    uiState: BeekeeperUiState,
    onToggleListing: (ProductDto, Boolean, Double?) -> Unit,
    onViewQr: (ProductDto) -> Unit,
    onAddEvent: (ProductDto) -> Unit,
    onRequestAdd: () -> Unit
) {
    if (uiState.selectedBatch == null) {
        EmptyView(
            title = "No Batch Selected",
            message = "Select a batch from step 2 to bottle and generate digital trace passports.",
            icon = Icons.Default.Layers
        )
    } else if (uiState.products.isEmpty()) {
        EmptyView(
            title = "No Bottled Products in Batch #${uiState.selectedBatch.batchNumber}",
            message = "Package jars (e.g. 500g) with unique blockchain-trace tokens.",
            icon = Icons.Default.Inventory2,
            actionLabel = "Bottle Product",
            onAction = onRequestAdd
        )
    } else {
        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(12.dp),
            contentPadding = PaddingValues(bottom = 80.dp)
        ) {
            items(uiState.products, key = { it.id }) { product ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
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
                            Text(
                                text = product.title,
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.weight(1f)
                            )
                            Row(
                                horizontalArrangement = Arrangement.spacedBy(6.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                if (product.isListed == true) {
                                    Surface(
                                        color = MaterialTheme.colorScheme.primaryContainer,
                                        shape = RoundedCornerShape(12.dp)
                                    ) {
                                        Text(
                                            text = "Listed in Shop",
                                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                                            style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.onPrimaryContainer,
                                            fontWeight = FontWeight.Bold
                                        )
                                    }
                                } else {
                                    Surface(
                                        color = MaterialTheme.colorScheme.surfaceVariant,
                                        shape = RoundedCornerShape(12.dp)
                                    ) {
                                        Text(
                                            text = "Unlisted",
                                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                                            style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                            fontWeight = FontWeight.Medium
                                        )
                                    }
                                }
                                StatusBadge(status = product.status)
                            }
                        }

                        Text(
                            text = "${product.jarSizeGrams}g Jar • Price: ₹${product.price.toInt()} • Token: ${product.traceToken}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            OutlinedButton(
                                onClick = { onViewQr(product) },
                                shape = RoundedCornerShape(8.dp),
                                modifier = Modifier.weight(1f)
                            ) {
                                Icon(Icons.Default.QrCode, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("QR Code")
                            }

                            OutlinedButton(
                                onClick = { onAddEvent(product) },
                                shape = RoundedCornerShape(8.dp),
                                modifier = Modifier.weight(1f)
                            ) {
                                Icon(Icons.Default.Event, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Add Event")
                            }
                        }

                        val isCurrentlyListed = product.isListed == true
                        Button(
                            onClick = { onToggleListing(product, !isCurrentlyListed, product.price) },
                            shape = RoundedCornerShape(8.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (isCurrentlyListed)
                                    MaterialTheme.colorScheme.errorContainer
                                else
                                    MaterialTheme.colorScheme.primary,
                                contentColor = if (isCurrentlyListed)
                                    MaterialTheme.colorScheme.onErrorContainer
                                else
                                    MaterialTheme.colorScheme.onPrimary
                            ),
                            modifier = Modifier
                                .fillMaxWidth()
                                .heightIn(min = 48.dp)
                                .testTag("product_toggle_listing_${product.id}")
                        ) {
                            Icon(
                                imageVector = if (isCurrentlyListed) Icons.Default.VisibilityOff else Icons.Default.ShoppingCart,
                                contentDescription = null,
                                modifier = Modifier.size(18.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = if (isCurrentlyListed) "Unlist from Marketplace" else "List in Public Marketplace",
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }
                }
            }
        }
    }
}

// Dialogs
@Composable
private fun CreateHarvestDialog(
    hiveCode: String,
    onDismiss: () -> Unit,
    onCreate: (date: String, qty: Double, moisture: Double?, flora: String?, notes: String?) -> Unit
) {
    var date by remember { mutableStateOf("2026-05-15") }
    var qty by remember { mutableStateOf("15.0") }
    var moisture by remember { mutableStateOf("17.8") }
    var flora by remember { mutableStateOf("Multiflora Forest") }
    var notes by remember { mutableStateOf("High viscosity, golden amber") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Log Harvest from Hive $hiveCode") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                HoneyOutlinedTextField(value = date, onValueChange = { date = it }, label = "Harvest Date (YYYY-MM-DD)")
                HoneyOutlinedTextField(value = qty, onValueChange = { qty = it }, label = "Quantity (kg)")
                HoneyOutlinedTextField(value = moisture, onValueChange = { moisture = it }, label = "Moisture % (KVIC < 20%)")
                HoneyOutlinedTextField(value = flora, onValueChange = { flora = it }, label = "Floral Source")
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val q = qty.toDoubleOrNull() ?: 1.0
                    val m = moisture.toDoubleOrNull()
                    onCreate(date, q, m, flora, notes)
                }
            ) { Text("Save Harvest") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}

@Composable
private fun CreateBatchDialog(
    maxHarvestQty: Double,
    onDismiss: () -> Unit,
    onCreate: (batchNumber: String, totalKg: Double, flora: String?, grade: String) -> Unit
) {
    var batchNum by remember { mutableStateOf("BATCH-2026-001") }
    var qty by remember { mutableStateOf(maxHarvestQty.toString()) }
    var grade by remember { mutableStateOf("A") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Create Batch (Max: ${maxHarvestQty}kg)") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                HoneyOutlinedTextField(value = batchNum, onValueChange = { batchNum = it }, label = "Batch Number")
                HoneyOutlinedTextField(
                    value = qty,
                    onValueChange = { qty = it },
                    label = "Total Batch Quantity (kg)",
                    errorMessage = if ((qty.toDoubleOrNull() ?: 0.0) > maxHarvestQty) "Cannot exceed harvest quantity ($maxHarvestQty kg)" else null,
                    isError = (qty.toDoubleOrNull() ?: 0.0) > maxHarvestQty
                )
                HoneyOutlinedTextField(value = grade, onValueChange = { grade = it }, label = "Quality Grade (e.g. A, B)")
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val q = qty.toDoubleOrNull() ?: maxHarvestQty
                    onCreate(batchNum, q, null, grade)
                },
                enabled = (qty.toDoubleOrNull() ?: 0.0) <= maxHarvestQty && batchNum.isNotBlank()
            ) { Text("Create") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}

@Composable
private fun CreateProductDialog(
    batchNumber: String,
    onDismiss: () -> Unit,
    onCreate: (title: String, desc: String?, jarSize: Int, price: Double) -> Unit
) {
    var title by remember { mutableStateOf("Pure Organic Multiflora Honey") }
    var jarSize by remember { mutableStateOf("500") }
    var price by remember { mutableStateOf("450.0") }
    var desc by remember { mutableStateOf("Raw unpasteurized honey bottled directly at the apiary.") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Bottle Product for $batchNumber") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                HoneyOutlinedTextField(value = title, onValueChange = { title = it }, label = "Product Title")
                HoneyOutlinedTextField(value = jarSize, onValueChange = { jarSize = it }, label = "Jar Size (grams)")
                HoneyOutlinedTextField(value = price, onValueChange = { price = it }, label = "Retail Price (₹)")
                HoneyOutlinedTextField(value = desc, onValueChange = { desc = it }, label = "Description")
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val sz = jarSize.toIntOrNull() ?: 500
                    val pr = price.toDoubleOrNull() ?: 0.0
                    onCreate(title, desc, sz, pr)
                },
                enabled = title.isNotBlank()
            ) { Text("Bottle & Anchor") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}

@Composable
private fun AddEventDialog(
    productId: String,
    onDismiss: () -> Unit,
    onAdd: (type: String, title: String, desc: String?, loc: String?) -> Unit
) {
    var type by remember { mutableStateOf("FILTERED") }
    var title by remember { mutableStateOf("Cold Filtered & Packed") }
    var desc by remember { mutableStateOf("Coarse filtered at room temperature to retain pollen and enzymes.") }
    var loc by remember { mutableStateOf("Apiary Honey Shed") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Add Chain Event") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                HoneyOutlinedTextField(value = type, onValueChange = { type = it }, label = "Event Type (e.g. FILTERED, TESTED)")
                HoneyOutlinedTextField(value = title, onValueChange = { title = it }, label = "Event Title")
                HoneyOutlinedTextField(value = desc, onValueChange = { desc = it }, label = "Description")
                HoneyOutlinedTextField(value = loc, onValueChange = { loc = it }, label = "Location")
            }
        },
        confirmButton = {
            Button(onClick = { onAdd(type, title, desc, loc) }, enabled = title.isNotBlank()) {
                Text("Append Event")
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}

@Composable
private fun ProductQrDialog(
    product: ProductDto,
    qrResponse: QrResponseDto?,
    onDismiss: () -> Unit
) {
    // Use the public /trace/{trace_token}/qr endpoint — no auth required
    val baseUrl = BuildConfig.BACKEND_BASE_URL.trimEnd('/')
    val traceToken = product.traceToken
    val qrImageUrl = "$baseUrl/trace/$traceToken/qr"
    val tracePageUrl = "$baseUrl/trace/$traceToken"

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Digital Passport QR Code") },
        text = {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                // Real QR image loaded from backend via Coil
                Card(
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = androidx.compose.ui.graphics.Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                    modifier = Modifier.size(200.dp)
                ) {
                    SubcomposeAsyncImage(
                        model = ImageRequest.Builder(LocalContext.current)
                            .data(qrImageUrl)
                            .crossfade(true)
                            .build(),
                        contentDescription = "QR Code for ${product.traceToken}",
                        contentScale = ContentScale.Fit,
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(8.dp),
                        loading = {
                            Box(
                                modifier = Modifier.fillMaxSize(),
                                contentAlignment = Alignment.Center
                            ) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(32.dp),
                                    color = MaterialTheme.colorScheme.primary
                                )
                            }
                        },
                        error = {
                            // Fallback: show a large QR icon with the token text
                            Column(
                                modifier = Modifier.fillMaxSize(),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.QrCode2,
                                    contentDescription = "QR Code",
                                    modifier = Modifier.size(80.dp),
                                    tint = MaterialTheme.colorScheme.primary
                                )
                                Text(
                                    text = "Tap to retry",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    )
                }

                // Trace token label
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.primaryContainer,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier.padding(10.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Text(
                            text = "Trace Token",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                        Text(
                            text = traceToken,
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer,
                            textAlign = TextAlign.Center
                        )
                    }
                }

                Text(
                    text = "Print or display this QR on the jar seal. Buyers scan it to verify the complete harvest origin and authenticity chain.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center
                )
            }
        },
        confirmButton = {
            Button(onClick = onDismiss) { Text("Done") }
        }
    )
}

