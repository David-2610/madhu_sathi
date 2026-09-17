package com.example.presentation.beekeeper

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
import com.example.data.remote.dto.HiveAlertDto

@Composable
fun BeekeeperIoTScreen(
    viewModel: BeekeeperViewModel
) {
    val uiState by viewModel.uiState.collectAsState()

    var tempInput by remember { mutableStateOf("35.0") }
    var humidityInput by remember { mutableStateOf("55.0") }
    var weightInput by remember { mutableStateOf("28.4") }

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Selected Hive Banner
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
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
                    Column {
                        Text(
                            text = "Inspecting Hive",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = if (uiState.selectedHive != null) "Hive #${uiState.selectedHive!!.hiveNumber}" else "No Hive Selected",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    StatusBadge(status = uiState.hiveHealth?.status ?: "NORMAL")
                }
            }

            if (uiState.selectedHive == null) {
                EmptyView(
                    title = "No Hive Selected",
                    message = "Pick an active hive from the Hives tab to view IoT telemetry and colony health.",
                    icon = Icons.Default.Sensors
                )
            } else {
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(bottom = 80.dp)
                ) {
                    // Metrics Overview
                    item {
                        Text(
                            text = "Colony Vital Telemetry",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            StatCard(
                                title = "Brood Temp",
                                value = "${uiState.hiveHealth?.temperatureC ?: 35.0}°C",
                                subtitle = "Normal: 34-36°C",
                                icon = Icons.Default.DeviceThermostat,
                                modifier = Modifier.weight(1f)
                            )
                            StatCard(
                                title = "Internal Humidity",
                                value = "${uiState.hiveHealth?.humidityPct ?: 55.0}%",
                                subtitle = "Normal: 50-65%",
                                icon = Icons.Default.Water,
                                modifier = Modifier.weight(1f)
                            )
                        }
                        Spacer(modifier = Modifier.height(12.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            StatCard(
                                title = "Hive Weight",
                                value = "${uiState.hiveHealth?.weightKg ?: 28.5} kg",
                                subtitle = "Nectar & Honey Reserve",
                                icon = Icons.Default.Scale,
                                modifier = Modifier.weight(1f)
                            )
                            StatCard(
                                title = "Health Index",
                                value = "${uiState.hiveHealth?.healthScore ?: 96}/100",
                                subtitle = "Colony Vitality",
                                icon = Icons.Default.Favorite,
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }

                    // Telemetry Ingestion / Hardware Simulator Section
                    item {
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
                                        text = "Sensor Telemetry Ingestion",
                                        style = MaterialTheme.typography.titleSmall,
                                        fontWeight = FontWeight.Bold
                                    )
                                    StatusBadge(status = "ESP32 IOT READY")
                                }

                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    HoneyOutlinedTextField(
                                        value = tempInput,
                                        onValueChange = { tempInput = it },
                                        label = "Temp (°C)",
                                        modifier = Modifier.weight(1f)
                                    )
                                    HoneyOutlinedTextField(
                                        value = humidityInput,
                                        onValueChange = { humidityInput = it },
                                        label = "Humidity (%)",
                                        modifier = Modifier.weight(1f)
                                    )
                                    HoneyOutlinedTextField(
                                        value = weightInput,
                                        onValueChange = { weightInput = it },
                                        label = "Weight (kg)",
                                        modifier = Modifier.weight(1f)
                                    )
                                }

                                HoneyButton(
                                    text = "Ingest Telemetry Reading",
                                    onClick = {
                                        val t = tempInput.toDoubleOrNull() ?: 35.0
                                        val h = humidityInput.toDoubleOrNull() ?: 55.0
                                        val w = weightInput.toDoubleOrNull() ?: 28.0
                                        viewModel.submitTelemetry(uiState.selectedHive!!.id, t, h, w)
                                    },
                                    isLoading = uiState.isLoading,
                                    icon = Icons.Default.Sensors
                                )

                                HorizontalDivider()

                                // Simulator Card
                                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                    Text(
                                        text = "Safety Simulation Mode",
                                        style = MaterialTheme.typography.labelMedium,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                    Text(
                                        text = "Trigger a full automated IoT cycle simulation via the backend simulator engine.",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                    OutlinedButton(
                                        onClick = { viewModel.runSimulator(uiState.selectedHive!!.id) },
                                        enabled = !uiState.isSimulating,
                                        modifier = Modifier.fillMaxWidth(),
                                        shape = RoundedCornerShape(8.dp)
                                    ) {
                                        Icon(Icons.Default.PlayArrow, contentDescription = null)
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Text(if (uiState.isSimulating) "Simulating IoT Cycles..." else "Run Backend Simulator")
                                    }
                                }
                            }
                        }
                    }

                    // Alerts Section
                    item {
                        Text(
                            text = "Active Colony Alerts (${uiState.alerts.count { !it.isResolved }})",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold
                        )
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
                                onAcknowledge = {
                                    viewModel.acknowledgeAlert(alert.id, uiState.selectedHive!!.id)
                                },
                                onResolve = {
                                    viewModel.resolveAlert(alert.id, uiState.selectedHive!!.id)
                                }
                            )
                        }
                    }
                }
            }
        }
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
                MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.3f)
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
