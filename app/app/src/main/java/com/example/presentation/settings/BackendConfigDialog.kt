package com.example.presentation.settings

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Dns
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.core.network.ApiResult
import com.example.core.ui.HoneyButton
import com.example.core.ui.HoneyOutlinedTextField
import com.example.data.repository.AuthRepository
import kotlinx.coroutines.launch

@Composable
fun BackendConfigDialog(
    currentUrl: String,
    authRepository: AuthRepository,
    onDismiss: () -> Unit,
    onSaved: (String) -> Unit
) {
    var urlText by remember { mutableStateOf(currentUrl) }
    var testStatus by remember { mutableStateOf<String?>(null) }
    var isTesting by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Dns,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary
                )
                Text("Backend Base URL", fontWeight = FontWeight.Bold)
            }
        },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = "Configure the FastAPI server address. Use http://10.0.2.2:8000/ on the Android emulator or your LAN IP (e.g. http://192.168.x.x:8000/) on physical devices.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                HoneyOutlinedTextField(
                    value = urlText,
                    onValueChange = { urlText = it },
                    label = "Base URL",
                    placeholder = "http://10.0.2.2:8000/"
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedButton(
                        onClick = {
                            scope.launch {
                                isTesting = true
                                testStatus = "Testing connection..."
                                val res = authRepository.checkHealth()
                                isTesting = false
                                testStatus = when (res) {
                                    is ApiResult.Success -> "Connected! Status: ${res.data.status}"
                                    is ApiResult.Error -> "Connection failed: ${res.message}"
                                    else -> null
                                }
                            }
                        },
                        enabled = !isTesting,
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.weight(1f)
                    ) {
                        Text(if (isTesting) "Pinging..." else "Test Health")
                    }

                    OutlinedButton(
                        onClick = { urlText = "http://10.0.2.2:8000/" },
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Reset Emulator")
                    }
                }

                if (testStatus != null) {
                    Text(
                        text = testStatus.orEmpty(),
                        style = MaterialTheme.typography.bodySmall,
                        color = if (testStatus?.startsWith("Connected") == true)
                            MaterialTheme.colorScheme.primary
                        else
                            MaterialTheme.colorScheme.error,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val finalUrl = if (urlText.endsWith("/")) urlText else "$urlText/"
                    scope.launch {
                        authRepository.updateBackendUrl(finalUrl)
                        onSaved(finalUrl)
                        onDismiss()
                    }
                },
                shape = RoundedCornerShape(8.dp)
            ) {
                Text("Save & Apply")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}
