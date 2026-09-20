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
import com.example.data.remote.dto.ApiaryDto

@Composable
fun BeekeeperApiariesScreen(
    viewModel: BeekeeperViewModel,
    onApiarySelected: (ApiaryDto) -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    var showCreateDialog by remember { mutableStateOf(false) }

    if (showCreateDialog) {
        CreateApiaryDialog(
            onDismiss = { showCreateDialog = false },
            onCreate = { name, loc, flora ->
                viewModel.createApiary(name, loc, flora)
                showCreateDialog = false
            }
        )
    }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showCreateDialog = true },
                modifier = Modifier.testTag("add_apiary_fab")
            ) {
                Icon(Icons.Default.Add, contentDescription = "Add Apiary")
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
            if (uiState.isLoading && uiState.apiaries.isEmpty()) {
                LoadingView(message = "Loading apiaries...")
            } else if (uiState.apiaries.isEmpty()) {
                EmptyView(
                    title = "No Apiaries Registered",
                    message = "Register your first bee yard location to begin tracking hives and harvests.",
                    icon = Icons.Default.Terrain,
                    actionLabel = "Add Apiary",
                    onAction = { showCreateDialog = true }
                )
            } else {
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(bottom = 80.dp)
                ) {
                    items(uiState.apiaries, key = { it.id }) { apiary ->
                        val isSelected = uiState.selectedApiary?.id == apiary.id
                        ApiaryCard(
                            apiary = apiary,
                            isSelected = isSelected,
                            onClick = {
                                viewModel.selectApiary(apiary)
                                onApiarySelected(apiary)
                            }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ApiaryCard(
    apiary: ApiaryDto,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() }
            .testTag("apiary_card_${apiary.id}"),
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
                    text = apiary.name,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "📍 ${apiary.locationName ?: "Registered Location"}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                if (!apiary.floraType.isNullOrBlank()) {
                    Text(
                        text = "🌸 Flora: ${apiary.floraType}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }

            Column(horizontalAlignment = Alignment.End) {
                StatusBadge(status = "${apiary.hiveCount ?: 0} HIVES")
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
private fun CreateApiaryDialog(
    onDismiss: () -> Unit,
    onCreate: (name: String, location: String?, flora: String?) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var location by remember { mutableStateOf("") }
    var flora by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Register Apiary") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                HoneyOutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = "Apiary Name",
                    placeholder = "e.g. Nilgiri Valley Yard"
                )
                HoneyOutlinedTextField(
                    value = location,
                    onValueChange = { location = it },
                    label = "Location / District",
                    placeholder = "e.g. Ooty, Tamil Nadu"
                )
                HoneyOutlinedTextField(
                    value = flora,
                    onValueChange = { flora = it },
                    label = "Dominant Flora / Nectar Source",
                    placeholder = "e.g. Eucalyptus, Mustard, Multiflora"
                )
            }
        },
        confirmButton = {
            Button(
                onClick = { onCreate(name, location, flora) },
                enabled = name.isNotBlank()
            ) {
                Text("Register")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}
