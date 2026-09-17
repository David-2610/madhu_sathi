package com.example.presentation.beekeeper

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.core.ui.HoneyButton
import com.example.core.ui.HoneyOutlinedTextField
import com.example.core.ui.StatusBadge
import com.example.data.local.entity.UserProfileEntity
import com.example.data.remote.dto.BeekeeperProfileDto
import com.example.data.sync.HoneyChainSyncWorker

@Composable
fun BeekeeperProfileScreen(
    viewModel: BeekeeperViewModel,
    userProfile: UserProfileEntity?,
    backendUrl: String,
    onOpenBackendConfig: () -> Unit,
    onLogout: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    var stateText by remember { mutableStateOf("") }
    var districtText by remember { mutableStateOf("") }
    var pincodeText by remember { mutableStateOf("") }
    var expYearsText by remember { mutableStateOf("") }
    var certNumberText by remember { mutableStateOf("") }
    var bioText by remember { mutableStateOf("") }

    LaunchedEffect(uiState.profile) {
        uiState.profile?.let { p ->
            stateText = p.state ?: ""
            districtText = p.district ?: ""
            pincodeText = p.pincode ?: ""
            expYearsText = p.experienceYears?.toString() ?: ""
            certNumberText = p.certificationNumber ?: ""
            bioText = p.bio ?: ""
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Beekeeper header
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = userProfile?.fullName ?: "Beekeeper Producer",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    StatusBadge(status = "CERTIFIED BEEKEEPER")
                }
                Text(
                    text = userProfile?.email ?: "beekeeper@honeychain.org",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }

        // Profile Form
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(
                    text = "Professional Accreditation",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold
                )

                HoneyOutlinedTextField(
                    value = certNumberText,
                    onValueChange = { certNumberText = it },
                    label = "KVIC / Government Accreditation No.",
                    placeholder = "e.g. KVIC-AP-2026-99"
                )

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    HoneyOutlinedTextField(
                        value = stateText,
                        onValueChange = { stateText = it },
                        label = "State",
                        modifier = Modifier.weight(1f)
                    )
                    HoneyOutlinedTextField(
                        value = districtText,
                        onValueChange = { districtText = it },
                        label = "District",
                        modifier = Modifier.weight(1f)
                    )
                }

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    HoneyOutlinedTextField(
                        value = pincodeText,
                        onValueChange = { pincodeText = it },
                        label = "PIN Code",
                        modifier = Modifier.weight(1f)
                    )
                    HoneyOutlinedTextField(
                        value = expYearsText,
                        onValueChange = { expYearsText = it },
                        label = "Experience (Years)",
                        modifier = Modifier.weight(1f)
                    )
                }

                HoneyOutlinedTextField(
                    value = bioText,
                    onValueChange = { bioText = it },
                    label = "Apiary Bio & Flora Description",
                    placeholder = "Specializing in wild forest flora, cold-settled raw comb honey...",
                    singleLine = false,
                    modifier = Modifier.heightIn(min = 90.dp)
                )

                HoneyButton(
                    text = "Save Profile Details",
                    onClick = {
                        viewModel.saveProfile(
                            BeekeeperProfileDto(
                                state = stateText.ifBlank { null },
                                district = districtText.ifBlank { null },
                                pincode = pincodeText.ifBlank { null },
                                experienceYears = expYearsText.toIntOrNull(),
                                bio = bioText.ifBlank { null },
                                certificationNumber = certNumberText.ifBlank { null }
                            )
                        )
                    },
                    isLoading = uiState.isLoading,
                    icon = Icons.Default.Save
                )
            }
        }

        // Diagnostics
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(text = "System Settings", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)

                OutlinedButton(
                    onClick = onOpenBackendConfig,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Icon(Icons.Default.Dns, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Backend Server: ${backendUrl.removePrefix("http://")}")
                }

                OutlinedButton(
                    onClick = { HoneyChainSyncWorker.triggerOneTimeSync(context) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Icon(Icons.Default.Sync, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Sync Data (WorkManager)")
                }
            }
        }

        Button(
            onClick = onLogout,
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp)
                .testTag("beekeeper_logout_button"),
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.errorContainer,
                contentColor = MaterialTheme.colorScheme.onErrorContainer
            ),
            shape = RoundedCornerShape(10.dp)
        ) {
            Icon(Icons.Default.Logout, contentDescription = null, modifier = Modifier.size(18.dp))
            Spacer(modifier = Modifier.width(8.dp))
            Text("Sign Out", fontWeight = FontWeight.SemiBold)
        }
    }
}
