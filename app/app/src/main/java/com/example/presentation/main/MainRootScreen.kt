package com.example.presentation.main

import androidx.compose.animation.Crossfade
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.example.HoneyChainApplication
import com.example.core.navigation.Role
import com.example.core.ui.LoadingView
import com.example.presentation.admin.AdminShellScreen
import com.example.presentation.admin.AdminViewModel
import com.example.presentation.auth.AuthViewModel
import com.example.presentation.auth.LoginScreen
import com.example.presentation.auth.RegisterScreen
import com.example.presentation.beekeeper.BeekeeperShellScreen
import com.example.presentation.beekeeper.BeekeeperViewModel
import com.example.presentation.buyer.BuyerShellScreen
import com.example.presentation.buyer.BuyerViewModel

import com.example.presentation.trace.QrTraceScannerScreen
import com.example.presentation.trace.TraceViewModel

@Composable
fun MainRootScreen(
    app: HoneyChainApplication,
    mainViewModel: MainViewModel
) {
    val mainUiState by mainViewModel.uiState.collectAsState()

    // Scoped ViewModels
    val authViewModel = remember { AuthViewModel(app.authRepository) }
    val buyerViewModel = remember { BuyerViewModel(app.buyerRepository) }
    val beekeeperViewModel = remember { BeekeeperViewModel(app.beekeeperRepository, app.networkModule.webSocketManager) }
    val traceViewModel = remember { TraceViewModel(app.traceabilityRepository) }
    val adminViewModel = remember {
        AdminViewModel(app.adminRepository, app.traceabilityRepository, app.networkModule.webSocketManager)
    }

    var isRegistering by remember { mutableStateOf(false) }



    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        if (mainUiState.isPublicTraceActive) {
            // Public non-authenticated QR trace passport viewer
            QrTraceScannerScreen(
                viewModel = traceViewModel,
                canNavigateBack = true,
                onNavigateBack = { mainViewModel.setPublicTraceActive(false) }
            )
        } else {
            Crossfade(
                targetState = mainUiState.authState,
                label = "auth_crossfade"
            ) { state ->
                when (state) {
                    is AuthState.Loading -> {
                        Box(
                            modifier = Modifier.fillMaxSize(),
                            contentAlignment = Alignment.Center
                        ) {
                            LoadingView(message = "Connecting to Honey Chain...")
                        }
                    }

                    is AuthState.Unauthenticated -> {
                        if (isRegistering) {
                            RegisterScreen(
                                viewModel = authViewModel,
                                onNavigateBack = { isRegistering = false },
                                onRegistrationSuccess = { isRegistering = false }
                            )
                        } else {
                            LoginScreen(
                                viewModel = authViewModel,

                                onNavigateToRegister = { isRegistering = true },
                                onNavigateToPublicTrace = { mainViewModel.setPublicTraceActive(true) },
                                onLoginSuccess = { role ->
                                    mainViewModel.onLoginSuccess(role)
                                }
                            )
                        }
                    }

                    is AuthState.Authenticated -> {
                        when (state.role) {
                            Role.BUYER -> {
                                BuyerShellScreen(
                                    buyerViewModel = buyerViewModel,
                                    traceViewModel = traceViewModel,
                                    userProfile = state.userProfile,

                                    onLogout = { mainViewModel.logout() }
                                )
                            }

                            Role.BEEKEEPER -> {
                                BeekeeperShellScreen(
                                    viewModel = beekeeperViewModel,
                                    userProfile = state.userProfile,

                                    onLogout = { mainViewModel.logout() }
                                )
                            }

                            Role.KVIC_ADMIN -> {
                                AdminShellScreen(
                                    adminViewModel = adminViewModel,
                                    traceViewModel = traceViewModel,
                                    userProfile = state.userProfile,

                                    onLogout = { mainViewModel.logout() }
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
