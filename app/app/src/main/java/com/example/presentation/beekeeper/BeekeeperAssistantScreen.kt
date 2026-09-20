package com.example.presentation.beekeeper

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.core.ui.EmptyView
import com.example.core.ui.HoneyButton
import com.example.core.ui.HoneyOutlinedTextField
import com.example.core.ui.StatusBadge

@Composable
fun BeekeeperAssistantScreen(
    viewModel: BeekeeperViewModel
) {
    val uiState by viewModel.uiState.collectAsState()
    var questionText by remember { mutableStateOf("") }

    val quickQuestions = listOf(
        "Why is brood temperature below 34°C?",
        "How to prevent colony swarming this season?",
        "What is optimal moisture for KVIC grade A?",
        "Signs of varroa mite infestation in comb?"
    )

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
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
                            text = "Consulting for Colony",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = if (uiState.selectedHive != null) "Hive ${uiState.selectedHive!!.hiveCode}" else "Select a hive",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    StatusBadge(status = "AI ADVISOR")
                }
            }

            if (uiState.selectedHive == null) {
                EmptyView(
                    title = "No Hive Selected",
                    message = "Please select a hive to enable contextual AI colony diagnosis.",
                    icon = Icons.Default.Hive
                )
            } else {
                // Pre-filled Prompt Chips
                Text(
                    text = "Common Field Questions",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold
                )

                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    items(quickQuestions) { q ->
                        SuggestionChip(
                            onClick = { questionText = q },
                            label = { Text(q) }
                        )
                    }
                }

                // Question Form
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
                            text = "Ask Apiary Specialist",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold
                        )

                        HoneyOutlinedTextField(
                            value = questionText,
                            onValueChange = { questionText = it },
                            label = "Colony or Honey Query",
                            placeholder = "Describe observations, comb appearance, or sensor dips...",
                            singleLine = false,
                            modifier = Modifier.heightIn(min = 100.dp)
                        )

                        HoneyButton(
                            text = "Analyze & Recommend",
                            onClick = { viewModel.askAssistant(uiState.selectedHive!!.id, questionText) },
                            isLoading = uiState.isAskingAssistant,
                            icon = Icons.Default.Psychology
                        )
                    }
                }

                // AI Response Card
                if (uiState.assistantResponse != null) {
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
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Psychology,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.primary
                                )
                                Text(
                                    text = "Apiary Diagnostic Assessment",
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.Bold
                                )
                            }

                            Text(
                                text = uiState.assistantResponse!!.answer,
                                style = MaterialTheme.typography.bodyMedium
                            )

                            if (uiState.assistantResponse!!.recommendations.isNotEmpty()) {
                                HorizontalDivider()
                                Text(
                                    text = "Recommended Actions:",
                                    style = MaterialTheme.typography.labelMedium,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary
                                )

                                uiState.assistantResponse!!.recommendations.forEach { rec ->
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                                    ) {
                                        Text("✔", color = MaterialTheme.colorScheme.primary)
                                        Text(text = rec, style = MaterialTheme.typography.bodySmall)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
