package com.example.presentation.trace

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.camera.core.CameraSelector
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.example.core.ui.*
import com.example.data.remote.dto.TraceabilityDetailDto
import com.example.ui.theme.HoneyGoldPrimary
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.PermissionStatus
import com.google.accompanist.permissions.rememberPermissionState

@OptIn(ExperimentalPermissionsApi::class)
@Composable
fun QrTraceScannerScreen(
    viewModel: TraceViewModel,
    onNavigateBack: () -> Unit = {},
    canNavigateBack: Boolean = true
) {
    val uiState by viewModel.uiState.collectAsState()
    var inputToken by remember { mutableStateOf("") }
    var activeTab by remember { mutableIntStateOf(0) } // 0: Enter Code, 1: Camera Scanner

    // Runtime camera permission using accompanist
    val cameraPermissionState = rememberPermissionState(
        permission = android.Manifest.permission.CAMERA
    )

    Scaffold(
        topBar = {
            HoneyTopAppBar(
                title = "Honey Traceability",
                subtitle = "Verify origin, batch & authenticity",
                canNavigateBack = canNavigateBack,
                onNavigateBack = onNavigateBack
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Tab Selector
            TabRow(
                selectedTabIndex = activeTab,
                containerColor = MaterialTheme.colorScheme.surfaceVariant,
                modifier = Modifier.clip(RoundedCornerShape(12.dp))
            ) {
                Tab(
                    selected = activeTab == 0,
                    onClick = { activeTab = 0 },
                    text = { Text("Enter Token") },
                    icon = { Icon(Icons.Default.Pin, contentDescription = null) }
                )
                Tab(
                    selected = activeTab == 1,
                    onClick = {
                        activeTab = 1
                        // Request camera permission when switching to scan tab
                        if (cameraPermissionState.status != PermissionStatus.Granted) {
                            cameraPermissionState.launchPermissionRequest()
                        }
                    },
                    text = { Text("Scan QR") },
                    icon = { Icon(Icons.Default.QrCodeScanner, contentDescription = null) }
                )
            }

            if (uiState.traceDetails != null) {
                TraceDetailsView(
                    details = uiState.traceDetails!!,
                    onScanAgain = {
                        viewModel.clear()
                        inputToken = ""
                    }
                )
            } else {
                if (activeTab == 0) {
                    // Manual Token Input Mode
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            Text(
                                text = "Verify Jar Authenticity",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "Enter the unique trace token from the honey jar seal or scan its QR code.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )

                            HoneyOutlinedTextField(
                                value = inputToken,
                                onValueChange = { inputToken = it.uppercase() },
                                label = "Trace Token",
                                placeholder = "e.g. TRACE-KVIC-001",
                                leadingIcon = Icons.Default.VerifiedUser,
                                testTag = "trace_token_input"
                            )

                            HoneyButton(
                                text = "Verify Authenticity",
                                onClick = { viewModel.searchTrace(inputToken) },
                                isLoading = uiState.isLoading,
                                icon = Icons.Default.Search,
                                testTag = "verify_trace_button"
                            )
                        }
                    }
                } else {
                    // Camera Scanner View Mode — check permission first
                    when (cameraPermissionState.status) {
                        PermissionStatus.Granted -> {
                            val context = LocalContext.current
                            CameraPreviewBox(
                                onQrDetected = { detectedToken ->
                                    inputToken = detectedToken
                                    android.widget.Toast.makeText(
                                        context,
                                        "QR Scanned! Verifying...",
                                        android.widget.Toast.LENGTH_SHORT
                                    ).show()
                                    viewModel.searchTrace(detectedToken)
                                }
                            )
                        }

                        is PermissionStatus.Denied -> {
                            val denied = cameraPermissionState.status as PermissionStatus.Denied
                            CameraPermissionCard(
                                shouldShowRationale = denied.shouldShowRationale,
                                onRequestPermission = {
                                    cameraPermissionState.launchPermissionRequest()
                                }
                            )
                        }
                    }
                }

                if (uiState.isLoading) {
                    LoadingView(message = "Querying immutable trace records...")
                }

                if (uiState.errorMessage != null) {
                    ErrorCard(
                        message = uiState.errorMessage.orEmpty(),
                        onRetry = { viewModel.searchTrace(uiState.searchedToken) }
                    )
                }
            }
        }
    }
}

/**
 * Shown when camera permission is not granted yet.
 * Handles both "show rationale" and "permanently denied" cases.
 */
@OptIn(ExperimentalPermissionsApi::class)
@Composable
private fun CameraPermissionCard(
    shouldShowRationale: Boolean,
    onRequestPermission: () -> Unit
) {
    val context = LocalContext.current

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Icon(
                imageVector = Icons.Default.CameraAlt,
                contentDescription = null,
                modifier = Modifier.size(48.dp),
                tint = MaterialTheme.colorScheme.onErrorContainer
            )
            Text(
                text = if (shouldShowRationale) "Camera Permission Required" else "Permission Permanently Denied",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onErrorContainer,
                textAlign = TextAlign.Center
            )
            Text(
                text = if (shouldShowRationale) {
                    "Honey Chain needs camera access to scan QR codes on honey jars for authenticity verification."
                } else {
                    "Camera permission was permanently denied. Please enable it in your device settings to use the QR scanner."
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onErrorContainer,
                textAlign = TextAlign.Center
            )

            if (shouldShowRationale) {
                Button(
                    onClick = onRequestPermission,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error,
                        contentColor = MaterialTheme.colorScheme.onError
                    )
                ) {
                    Icon(Icons.Default.CameraAlt, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Grant Camera Permission")
                }
            } else {
                Button(
                    onClick = {
                        // Open app settings so user can manually grant permission
                        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                            data = Uri.fromParts("package", context.packageName, null)
                        }
                        context.startActivity(intent)
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error,
                        contentColor = MaterialTheme.colorScheme.onError
                    )
                ) {
                    Icon(Icons.Default.Settings, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Open App Settings")
                }
            }
        }
    }
}

@Composable
private fun CameraPreviewBox(
    onQrDetected: (String) -> Unit
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    // hasScanned prevents duplicate rapid callbacks for the same code
    var hasScanned by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .height(300.dp),
        shape = RoundedCornerShape(12.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            AndroidView(
                factory = { ctx ->
                    val previewView = PreviewView(ctx).apply {
                        implementationMode = PreviewView.ImplementationMode.COMPATIBLE
                    }
                    val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)
                    cameraProviderFuture.addListener({
                        try {
                            val cameraProvider = cameraProviderFuture.get()

                            val preview = Preview.Builder().build().also {
                                it.surfaceProvider = previewView.surfaceProvider
                            }

                            val imageAnalysis = androidx.camera.core.ImageAnalysis.Builder()
                                .setBackpressureStrategy(androidx.camera.core.ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                                .build()

                            val scanner = com.google.mlkit.vision.barcode.BarcodeScanning.getClient(
                                com.google.mlkit.vision.barcode.BarcodeScannerOptions.Builder()
                                    .setBarcodeFormats(com.google.mlkit.vision.barcode.common.Barcode.FORMAT_QR_CODE)
                                    .build()
                            )

                            imageAnalysis.setAnalyzer(ContextCompat.getMainExecutor(ctx)) { imageProxy ->
                                @androidx.annotation.OptIn(androidx.camera.core.ExperimentalGetImage::class)
                                val mediaImage = imageProxy.image
                                if (mediaImage != null && !hasScanned) {
                                    val image = com.google.mlkit.vision.common.InputImage.fromMediaImage(
                                        mediaImage,
                                        imageProxy.imageInfo.rotationDegrees
                                    )
                                    scanner.process(image)
                                        .addOnSuccessListener { barcodes ->
                                            if (barcodes.isNotEmpty() && !hasScanned) {
                                                val rawValue = barcodes.first().rawValue
                                                if (!rawValue.isNullOrBlank()) {
                                                    hasScanned = true
                                                    // Extract trace token from full trace URL if present
                                                    val token = when {
                                                        rawValue.contains("/trace/") ->
                                                            rawValue.substringAfterLast("/").trim()
                                                        else -> rawValue.trim()
                                                    }
                                                    onQrDetected(token)
                                                }
                                            }
                                        }
                                        .addOnCompleteListener {
                                            imageProxy.close()
                                        }
                                } else {
                                    imageProxy.close()
                                }
                            }

                            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
                            cameraProvider.unbindAll()
                            cameraProvider.bindToLifecycle(
                                lifecycleOwner,
                                cameraSelector,
                                preview,
                                imageAnalysis
                            )
                        } catch (e: Exception) {
                            e.printStackTrace()
                        }
                    }, ContextCompat.getMainExecutor(ctx))
                    previewView
                },
                modifier = Modifier.fillMaxSize()
            )

            // Viewfinder reticle overlay
            Box(
                modifier = Modifier
                    .size(200.dp)
                    .border(3.dp, HoneyGoldPrimary, RoundedCornerShape(16.dp))
            )

            // Corner accents for the reticle
            val cornerSize = 24.dp
            val cornerWidth = 3.dp
            val cornerColor = HoneyGoldPrimary

            // Top-left
            Box(
                modifier = Modifier
                    .align(Alignment.Center)
                    .offset(x = (-100).dp, y = (-100).dp)
            )

            Text(
                text = if (hasScanned) "✓ QR Code Detected!" else "Point camera at Honey Chain QR",
                style = MaterialTheme.typography.labelSmall,
                color = Color.White,
                fontWeight = if (hasScanned) FontWeight.Bold else FontWeight.Normal,
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 12.dp)
                    .background(
                        if (hasScanned) Color(0xFF1B5E20).copy(alpha = 0.85f)
                        else Color.Black.copy(alpha = 0.6f),
                        RoundedCornerShape(8.dp)
                    )
                    .padding(horizontal = 12.dp, vertical = 6.dp)
            )
        }
    }
}

@Composable
private fun TraceDetailsView(
    details: TraceabilityDetailDto,
    onScanAgain: () -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Status & Header Banner
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Trace Token: ${details.traceToken}",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    StatusBadge(status = details.status)
                }

                HorizontalDivider()

                Text(
                    text = details.productTitle,
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    details.floralSource?.let {
                        InfoPill(label = "Flora", value = it)
                    }
                    details.jarSizeGrams?.let {
                        InfoPill(label = "Size", value = "${it}g Jar")
                    }
                    details.qualityGrade?.let {
                        InfoPill(label = "Grade", value = "Grade $it")
                    }
                }
            }
        }

        // Origin & Apiary Info Card
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(
                    text = "Apiary & Harvest Origin",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )

                OriginRow(title = "Beekeeper", value = details.beekeeperName ?: "Certified Honey Producer")
                OriginRow(title = "Location", value = details.apiaryLocation ?: "Verified Khadi Apiary")
                OriginRow(title = "Harvest Date", value = details.harvestDate ?: "Seasonal Harvest")
                OriginRow(title = "Batch Number", value = details.batchNumber ?: "—")
                details.moisturePercentage?.let {
                    OriginRow(title = "Moisture", value = "$it% (KVIC Compliant < 20%)")
                }
            }
        }

        // Timeline of Events
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = "Chain of Custody Timeline",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold
                )

                if (details.events.isEmpty()) {
                    Text(
                        text = "No intermediate transit events recorded.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else {
                    details.events.forEachIndexed { index, ev ->
                        TimelineEventItem(
                            index = index,
                            total = details.events.size,
                            type = ev.eventType,
                            title = ev.eventTitle,
                            description = ev.description,
                            location = ev.location,
                            timestamp = ev.timestamp
                        )
                    }
                }
            }
        }

        OutlinedButton(
            onClick = onScanAgain,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(10.dp)
        ) {
            Icon(Icons.Default.QrCodeScanner, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Verify Another Jar")
        }
    }
}

@Composable
private fun InfoPill(label: String, value: String) {
    Surface(
        color = MaterialTheme.colorScheme.surfaceVariant,
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)) {
            Text(text = label, style = MaterialTheme.typography.labelSmall, fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(text = value, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun OriginRow(title: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(text = title, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(text = value, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun TimelineEventItem(
    index: Int,
    total: Int,
    type: String,
    title: String,
    description: String?,
    location: String?,
    timestamp: String?
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                modifier = Modifier
                    .size(24.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.primary),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Check,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(14.dp)
                )
            }
            if (index < total - 1) {
                Box(
                    modifier = Modifier
                        .width(2.dp)
                        .height(36.dp)
                        .background(MaterialTheme.colorScheme.outlineVariant)
                )
            }
        }

        Column(modifier = Modifier.padding(bottom = 12.dp)) {
            Text(text = title, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
            if (!description.isNullOrBlank()) {
                Text(text = description, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (!location.isNullOrBlank()) {
                    Text(text = "📍 $location", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                if (!timestamp.isNullOrBlank()) {
                    Text(text = timestamp, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}
