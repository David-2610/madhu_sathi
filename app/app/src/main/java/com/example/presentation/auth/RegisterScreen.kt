package com.example.presentation.auth

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import com.example.core.ui.HoneyButton
import com.example.core.ui.HoneyOutlinedTextField
import com.example.core.ui.HoneyTopAppBar

@Composable
fun RegisterScreen(
    viewModel: AuthViewModel,
    onNavigateBack: () -> Unit,
    onRegistrationSuccess: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    val focusManager = LocalFocusManager.current

    var fullName by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var passwordVisible by remember { mutableStateOf(false) }
    var selectedRole by remember { mutableStateOf("BUYER") } // Exactly BUYER or BEEKEEPER

    Scaffold(
        topBar = {
            HoneyTopAppBar(
                title = "Create Account",
                canNavigateBack = true,
                onNavigateBack = onNavigateBack
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .imePadding()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text(
                text = "Join Honey Chain",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.align(Alignment.Start)
            )

            Text(
                text = "Select your account type to get started. Beekeepers can log apiaries and honey batches; Buyers can purchase verified honey.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.align(Alignment.Start)
            )

            // Connectivity Test Widget before registration
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = when (uiState.healthSuccess) {
                    true -> MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.5f)
                    false -> MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.5f)
                    else -> MaterialTheme.colorScheme.surfaceVariant
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Server Health (GET /health)",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.SemiBold
                        )
                        Text(
                            text = uiState.healthStatus ?: "Tap refresh to ping /health",
                            style = MaterialTheme.typography.bodySmall,
                            color = when (uiState.healthSuccess) {
                                true -> MaterialTheme.colorScheme.primary
                                false -> MaterialTheme.colorScheme.error
                                else -> MaterialTheme.colorScheme.onSurfaceVariant
                            }
                        )
                    }
                    IconButton(
                        onClick = { viewModel.testHealthConnection() },
                        enabled = !uiState.isHealthTesting,
                        modifier = Modifier.size(36.dp)
                    ) {
                        if (uiState.isHealthTesting) {
                            CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                        } else {
                            Icon(
                                imageVector = Icons.Default.Refresh,
                                contentDescription = "Test GET /health",
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }
                }
            }

            // Role selection segment
            Text(
                text = "Select Account Role",
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.align(Alignment.Start)
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                FilterChip(
                    selected = selectedRole == "BUYER",
                    onClick = { selectedRole = "BUYER" },
                    label = { Text("Buyer (Customer)") },
                    leadingIcon = {
                        Icon(
                            imageVector = Icons.Default.ShoppingCart,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                    },
                    modifier = Modifier.weight(1f)
                )

                FilterChip(
                    selected = selectedRole == "BEEKEEPER",
                    onClick = { selectedRole = "BEEKEEPER" },
                    label = { Text("Beekeeper") },
                    leadingIcon = {
                        Icon(
                            imageVector = Icons.Default.Agriculture,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                    },
                    modifier = Modifier.weight(1f)
                )
            }

            // Error banner
            if (uiState.errorMessage != null) {
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Warning,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.error
                        )
                        Text(
                            text = uiState.errorMessage.orEmpty(),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onErrorContainer
                        )
                    }
                }
            }

            // Form inputs
            HoneyOutlinedTextField(
                value = fullName,
                onValueChange = {
                    fullName = it
                    viewModel.clearErrors()
                },
                label = "Full Name",
                placeholder = "Ramesh Kumar",
                isError = uiState.fieldErrors.containsKey("fullName"),
                errorMessage = uiState.fieldErrors["fullName"],
                leadingIcon = Icons.Default.Person,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
                testTag = "register_name_input"
            )

            HoneyOutlinedTextField(
                value = email,
                onValueChange = {
                    email = it
                    viewModel.clearErrors()
                },
                label = "Email Address",
                placeholder = "ramesh@example.com",
                isError = uiState.fieldErrors.containsKey("email"),
                errorMessage = uiState.fieldErrors["email"],
                leadingIcon = Icons.Default.Email,
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Email,
                    imeAction = ImeAction.Next
                ),
                testTag = "register_email_input"
            )

            HoneyOutlinedTextField(
                value = phone,
                onValueChange = {
                    phone = it
                    viewModel.clearErrors()
                },
                label = "Phone Number",
                placeholder = "9876543210",
                isError = uiState.fieldErrors.containsKey("phone"),
                errorMessage = uiState.fieldErrors["phone"],
                leadingIcon = Icons.Default.Phone,
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Phone,
                    imeAction = ImeAction.Next
                ),
                testTag = "register_phone_input"
            )

            HoneyOutlinedTextField(
                value = password,
                onValueChange = {
                    password = it
                    viewModel.clearErrors()
                },
                label = "Password (min 6 characters)",
                placeholder = "••••••••",
                isError = uiState.fieldErrors.containsKey("password"),
                errorMessage = uiState.fieldErrors["password"],
                leadingIcon = Icons.Default.Lock,
                visualTransformation = if (passwordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                trailingIcon = {
                    IconButton(onClick = { passwordVisible = !passwordVisible }) {
                        Icon(
                            imageVector = if (passwordVisible) Icons.Default.Visibility else Icons.Default.VisibilityOff,
                            contentDescription = null
                        )
                    }
                },
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Password,
                    imeAction = ImeAction.Done
                ),
                keyboardActions = KeyboardActions(
                    onDone = {
                        focusManager.clearFocus()
                        viewModel.register(email, password, fullName, selectedRole, phone, onRegistrationSuccess)
                    }
                ),
                testTag = "register_password_input"
            )

            Spacer(modifier = Modifier.height(8.dp))

            HoneyButton(
                text = "Register as $selectedRole",
                onClick = {
                    focusManager.clearFocus()
                    viewModel.register(email, password, fullName, selectedRole, phone, onRegistrationSuccess)
                },
                isLoading = uiState.isLoading,
                icon = Icons.Default.Check,
                testTag = "register_submit_button"
            )
        }
    }
}
