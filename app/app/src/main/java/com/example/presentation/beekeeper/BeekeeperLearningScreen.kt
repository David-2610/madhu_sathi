package com.example.presentation.beekeeper

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

data class LearningGuide(
    val title: String,
    val category: String,
    val summary: String,
    val details: List<String>
)

@Composable
fun BeekeeperLearningScreen() {
    val guides = listOf(
        LearningGuide(
            title = "KVIC Grade-A Honey Compliance",
            category = "Quality Standards",
            summary = "Key parameters required for Khadi & Village Industries certification.",
            details = listOf(
                "Moisture content must remain strictly under 20% to prevent wild fermentation.",
                "Fructose-to-Glucose (F/G) ratio must exceed 0.95 to ensure natural nectar profile.",
                "Hydroxymethylfurfural (HMF) must not exceed 80 mg/kg (indicator of fresh, unheated honey).",
                "Ensure stainless steel grade 304 extraction drums and coarse filtering only."
            )
        ),
        LearningGuide(
            title = "Seasonal Brood & Hive Temperature Care",
            category = "Colony Health",
            summary = "Maintaining optimal 34.5°C–35.5°C brood nest temperatures year-round.",
            details = listOf(
                "Winter: Reduce entrance gates and insulate hive tops to minimize thermal stress.",
                "Summer: Provide shaded apiary stands and continuous water sources within 50 meters.",
                "Check for sudden temperature drops below 32°C which indicate chilled brood or queen loss.",
                "Monitor acoustic hum for high-pitched piping before swarms depart."
            )
        ),
        LearningGuide(
            title = "Organic Pest & Mite Management",
            category = "Pest Control",
            summary = "Combating Varroa destructor and wax moth without chemical residues.",
            details = listOf(
                "Use bottom screened boards with sticky monitoring sheets to calculate daily mite drops.",
                "Apply Thymol or Oxalic acid vaporization during post-harvest non-flow periods.",
                "Freeze harvested frames at -12°C for 24 hours prior to storage to eradicate wax moth eggs.",
                "Maintain strong, populous colonies; weak hives should be united promptly."
            )
        )
    )

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(12.dp),
                contentPadding = PaddingValues(bottom = 80.dp)
            ) {
                items(guides.size) { i ->
                    val guide = guides[i]
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Surface(
                                color = MaterialTheme.colorScheme.surfaceVariant,
                                shape = RoundedCornerShape(6.dp)
                            ) {
                                Text(
                                    text = guide.category,
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.primary,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                                )
                            }

                            Text(
                                text = guide.title,
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )

                            Text(
                                text = guide.summary,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )

                            HorizontalDivider()

                            guide.details.forEach { pt ->
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    Text("•", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                                    Text(text = pt, style = MaterialTheme.typography.bodySmall)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
