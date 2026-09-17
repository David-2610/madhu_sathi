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
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.core.ui.*
import com.example.data.remote.dto.HiveDto

@Composable
fun BeekeeperHivesScreen(
    viewModel: BeekeeperViewModel,
    onHiveSelected: (HiveDto) -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    var showCreateDialog by remember { mutableStateOf(false) }

    if (showCreateDialog && uiState.selectedApiary != null) {
        CreateHiveDialog(
            apiaryName = uiState.selectedApiary!!.name,
            onDismiss = { showCreateDialog = false },
            onCreate = { number, species ->
                viewModel.createHive(uiState.selectedApiary!!.id, number, species)
                showCreateDialog = false
            }
        )
    }

    Scaffold(
        floatingActionButton = {
            if (uiState.selectedApiary != null) {
                FloatingActionButton(
                    onClick = { showCreateDialog = true },
                    modifier = Modifier.testTag("add_hive_fab")
                ) {
                    Icon(Icons.Default.Add, contentDescription = "Add Hive")
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
            // Selected Apiary header chip
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
                            text = "Selected Apiary",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = uiState.selectedApiary?.name ?: "No apiary selected",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    StatusBadge(status = "${uiState.hives.size} Hives")
                }
            }

            if (uiState.selectedApiary == null) {
                EmptyView(
                    title = "No Apiary Selected",
                    message = "Please register or select an apiary to view and manage its hives.",
                    icon = Icons.Default.Terrain
                )
            } else if (uiState.hives.isEmpty()) {
                EmptyView(
                    title = "No Hives in this Apiary",
                    message = "Add your first bee hive box to begin logging colony inspections and IoT telemetry.",
                    icon = Icons.Default.Hive,
                    actionLabel = "Add Hive",
                    onAction = { showCreateDialog = true }
                )
            } else {
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(bottom = 80.dp)
                ) {
                    items(uiState.hives, key = { it.id }) { hive ->
                        val isSelected = uiState.selectedHive?.id == hive.id
                        HiveCard(
                            hive = hive,
                            isSelected = isSelected,
                            onClick = {
                                viewModel.selectHive(hive)
                                onHiveSelected(hive)
                            }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun HiveCard(
    hive: HiveDto,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() }
            .testTag("hive_card_${hive.id}"),
        colors = CardDefaults.cardColors(
            containerColor = if (isSelected)
                MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f)
            else
                MaterialTheme.colorScheme.surface
        ),
        shape = RoundedCornerShape(12.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = "Hive #${hive.hiveNumber}",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "🐝 Species: ${hive.beeSpecies ?: "Apis cerana indica"}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = "Health Score: ${hive.healthScore ?: 100}/100",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            Column(horizontalAlignment = Alignment.End) {
                StatusBadge(status = hive.status)
                if (isSelected) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Active",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
    }
}

@Composable
private fun CreateHiveDialog(
    apiaryName: String,
    onDismiss: () -> Unit,
    onCreate: (number: String, species: String?) -> Unit
) {
    var hiveNumber by remember { mutableStateOf("") }
    var species by remember { mutableStateOf("Apis cerana indica") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Add Hive to $apiaryName") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                HoneyOutlinedTextField(
                    value = hiveNumber,
                    onValueChange = { hiveNumber = it },
                    label = "Hive Box Number / ID",
                    placeholder = "e.g. H-01"
                )
                HoneyOutlinedTextField(
                    value = species,
                    onValueChange = { species = it },
                    label = "Bee Species",
                    placeholder = "e.g. Apis cerana indica, Apis mellifera"
                )
            }
        },
        confirmButton = {
            Button(
                onClick = { onCreate(hiveNumber, species) },
                enabled = hiveNumber.isNotBlank()
            ) {
                Text("Add Hive")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}
