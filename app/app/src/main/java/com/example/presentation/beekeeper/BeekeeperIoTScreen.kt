package com.example.presentation.beekeeper

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.ui.unit.dp
import com.example.core.ui.*
import com.example.data.remote.dto.HiveAlertDto
import com.example.ui.theme.*

@Composable
fun BeekeeperIoTScreen(
    viewModel: BeekeeperViewModel
) {
    val uiState by viewModel.uiState.collectAsState()

    var showExternalServerConfig by remember { mutableStateOf(false) }
    var externalUrlInput by remember { mutableStateOf(uiState.iotServerUrl) }
    var selectedIntervalMs by remember { mutableLongStateOf(2000L) }

    val activeHive = uiState.selectedHive ?: uiState.hives.firstOrNull()

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Selected Hive and Status Header
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = "MONITORED HIVE",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                text = if (activeHive != null) "Hive ${activeHive.hiveCode}" else "Select a Hive",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                            if (uiState.isAutoStreaming) {
                                Surface(
                                    color = MaterialTheme.colorScheme.primaryContainer,
                                    shape = RoundedCornerShape(16.dp)
                                ) {
                                    Row(
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                                    ) {
                                        Box(
                                            modifier = Modifier
                                                .size(8.dp)
                                                .clip(CircleShape)
                                                .background(MaterialTheme.colorScheme.primary)
                                        )
                                        Text(
                                            text = "STREAMING #${uiState.streamPacketCount}",
                                            style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.onPrimaryContainer,
                                            fontWeight = FontWeight.Bold
                                        )
                                    }
                                }
                            }
                            StatusBadge(status = uiState.hiveHealth?.status ?: "NORMAL")
                        }
                    }

                    // Hive Switcher Chips if multiple hives exist
                    if (uiState.hives.size > 1) {
                        LazyRow(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            items(uiState.hives) { hive ->
                                val isSelected = activeHive?.id == hive.id
                                FilterChip(
                                    selected = isSelected,
                                    onClick = {
                                        viewModel.selectHive(hive)
                                    },
                                    label = { Text("Hive ${hive.hiveCode}") },
                                    leadingIcon = {
                                        Icon(Icons.Default.Hive, contentDescription = null, modifier = Modifier.size(16.dp))
                                    }
                                )
                            }
                        }
                    }
                }
            }

            if (activeHive == null) {
                EmptyView(
                    title = "No Hives Registered",
                    message = "Register an apiary and hive first to activate IoT telemetry monitoring and simulations.",
                    icon = Icons.Default.Sensors
                )
            } else {
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(14.dp),
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(bottom = 80.dp)
                ) {
                    // Vital Telemetry 5-Stat Matrix
                    item {
                        Text(
                            text = "Live Colony Telemetry & Atmosphere",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(6.dp))

                        // Row 1: Temperature and Humidity
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            val temp = uiState.hiveHealth?.temperatureC ?: uiState.currentTemp
                            TelemetryMetricCard(
                                title = "Brood Temp",
                                value = String.format("%.1f°C", temp),
                                status = when {
                                    temp in 34.5..35.5 -> "Optimal"
                                    temp in 32.0..37.5 -> "Acceptable"
                                    else -> "Critical Alert"
                                },
                                isAlert = temp < 32.0 || temp > 38.0,
                                icon = Icons.Default.DeviceThermostat,
                                modifier = Modifier.weight(1f)
                            )
                            val hum = uiState.hiveHealth?.humidityPct ?: uiState.currentHumidity
                            TelemetryMetricCard(
                                title = "Internal Humidity",
                                value = String.format("%.1f%%", hum),
                                status = when {
                                    hum in 50.0..65.0 -> "Optimal (50-65%)"
                                    hum in 45.0..75.0 -> "Moderate"
                                    else -> "Mold Risk (>75%)"
                                },
                                isAlert = hum < 40.0 || hum > 75.0,
                                icon = Icons.Default.Water,
                                modifier = Modifier.weight(1f)
                            )
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        // Row 2: Weight and Acoustic Sound
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            val weight = uiState.hiveHealth?.weightKg ?: uiState.currentWeight
                            TelemetryMetricCard(
                                title = "Hive Weight",
                                value = String.format("%.2f kg", weight),
                                status = "Nectar & Honey Reserve",
                                isAlert = false,
                                icon = Icons.Default.Scale,
                                modifier = Modifier.weight(1f)
                            )
                            val sound = uiState.hiveHealth?.soundLevelDb ?: uiState.currentSoundDb
                            TelemetryMetricCard(
                                title = "Acoustic Hum",
                                value = String.format("%.1f dB", sound),
                                status = when {
                                    sound < 55.0 -> "Normal Hum"
                                    sound < 80.0 -> "Agitation"
                                    else -> "Swarm / Piping Alert"
                                },
                                isAlert = sound > 85.0,
                                icon = Icons.Default.GraphicEq,
                                modifier = Modifier.weight(1f)
                            )
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        // Row 3: CO2 and Health Score
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            val co2 = uiState.hiveHealth?.co2Ppm ?: uiState.currentCo2Ppm
                            TelemetryMetricCard(
                                title = "Atmosphere CO2",
                                value = String.format("%.0f ppm", co2),
                                status = when {
                                    co2 < 800.0 -> "Fresh Air"
                                    co2 < 1200.0 -> "Elevated"
                                    else -> "Ventilation Needed"
                                },
                                isAlert = co2 > 1200.0,
                                icon = Icons.Default.Air,
                                modifier = Modifier.weight(1f)
                            )
                            val health = uiState.hiveHealth?.healthScore ?: 96
                            TelemetryMetricCard(
                                title = "Health Vitality",
                                value = "$health / 100",
                                status = if (health >= 80) "Colony Thriving" else if (health >= 50) "Watch Colony" else "Action Required",
                                isAlert = health < 50,
                                icon = Icons.Default.Favorite,
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }


                    // Interactive Scenario Presets (from IoT mock server)
                    item {
                        Card(
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(
                                        text = "Simulation Scenario Presets",
                                        style = MaterialTheme.typography.titleSmall,
                                        fontWeight = FontWeight.Bold
                                    )
                                    Text(
                                        text = "1-Tap Ingestion",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.primary,
                                        fontWeight = FontWeight.Bold
                                    )
                                }

                                val scenarios = listOf(
                                    Triple("HEALTHY", "Normal Colony", "34.8°C | 58% | 48dB"),
                                    Triple("OVERHEATING", "Overheating (Heat Stress)", "39.4°C | 44% | 78dB"),
                                    Triple("HUMIDITY", "High Humidity (Mold Risk)", "33.2°C | 85% | 52dB"),
                                    Triple("SWARM", "Swarm Piping Alert", "36.8°C | 52% | 96dB"),
                                    Triple("LOW_ACTIVITY", "Winter Chill / Low Brood", "29.8°C | 65% | 25dB")
                                )

                                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                    scenarios.forEach { (code, title, specs) ->
                                        val isSelected = uiState.selectedScenario == code
                                        Surface(
                                            onClick = { viewModel.applyPresetScenario(code, activeHive.id) },
                                            shape = RoundedCornerShape(8.dp),
                                            color = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                                            modifier = Modifier.fillMaxWidth()
                                        ) {
                                            Row(
                                                modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                                                horizontalArrangement = Arrangement.SpaceBetween,
                                                verticalAlignment = Alignment.CenterVertically
                                            ) {
                                                Column {
                                                    Text(
                                                        text = title,
                                                        style = MaterialTheme.typography.bodyMedium,
                                                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                                        color = if (isSelected) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSurface
                                                    )
                                                    Text(
                                                        text = specs,
                                                        style = MaterialTheme.typography.labelSmall,
                                                        color = if (isSelected) MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f) else MaterialTheme.colorScheme.onSurfaceVariant
                                                    )
                                                }
                                                Icon(
                                                    imageVector = if (isSelected) Icons.Default.CheckCircle else Icons.Default.PlayCircleOutline,
                                                    contentDescription = null,
                                                    tint = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }


                    // Alerts Section
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Active Colony Alerts (${uiState.alerts.count { !it.isResolved }})",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold
                            )
                            if (uiState.alerts.isNotEmpty()) {
                                TextButton(onClick = { viewModel.loadAlerts(activeHive.id) }) {
                                    Text("Refresh")
                                }
                            }
                        }
                    }

                    if (uiState.alerts.isEmpty()) {
                        item {
                            Card(
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                shape = RoundedCornerShape(10.dp),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Box(modifier = Modifier.padding(16.dp), contentAlignment = Alignment.Center) {
                                    Text(
                                        text = "No active warnings. Colony conditions are optimal.",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                        }
                    } else {
                        items(uiState.alerts, key = { it.id }) { alert ->
                            AlertItemCard(
                                alert = alert,
                                onAcknowledge = { viewModel.acknowledgeAlert(alert.id, activeHive.id) },
                                onResolve = { viewModel.resolveAlert(alert.id, activeHive.id) }
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TelemetryMetricCard(
    title: String,
    value: String,
    status: String,
    isAlert: Boolean,
    icon: ImageVector,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(
            containerColor = if (isAlert) MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.25f)
            else MaterialTheme.colorScheme.surface
        ),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = if (isAlert) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(18.dp)
                )
            }
            Text(
                text = value,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = if (isAlert) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = status,
                style = MaterialTheme.typography.labelSmall,
                color = if (isAlert) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun MetricSlider(
    label: String,
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    unit: String,
    onValueChange: (Float) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(text = label, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Medium)
            Text(text = "$value $unit", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
        }
        Slider(
            value = value,
            onValueChange = onValueChange,
            valueRange = range,
            modifier = Modifier.fillMaxWidth()
        )
    }
}

@Composable
private fun AlertItemCard(
    alert: HiveAlertDto,
    onAcknowledge: () -> Unit,
    onResolve: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (!alert.isResolved)
                MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.35f)
            else
                MaterialTheme.colorScheme.surface
        ),
        shape = RoundedCornerShape(10.dp)
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                StatusBadge(status = if (alert.isResolved) "RESOLVED" else alert.severity)
                Text(
                    text = alert.alertType,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Text(
                text = alert.message,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold
            )

            if (!alert.isResolved) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    if (!alert.isAcknowledged) {
                        OutlinedButton(
                            onClick = onAcknowledge,
                            modifier = Modifier.weight(1f),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Text("Acknowledge")
                        }
                    }

                    Button(
                        onClick = onResolve,
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text("Resolve Alert")
                    }
                }
            }
        }
    }
}
