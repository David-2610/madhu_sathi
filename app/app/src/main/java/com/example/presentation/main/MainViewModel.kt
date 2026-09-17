package com.example.presentation.main

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.core.navigation.Role
import com.example.core.network.ApiResult
import com.example.data.local.entity.UserProfileEntity
import com.example.data.repository.AuthRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeout

sealed interface AuthState {
    data object Loading : AuthState
    data object Unauthenticated : AuthState
    data class Authenticated(val role: Role, val userProfile: UserProfileEntity?) : AuthState
}

data class MainUiState(
    val authState: AuthState = AuthState.Loading,
    val isPublicTraceActive: Boolean = false
)

class MainViewModel(
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(MainUiState())
    val uiState: StateFlow<MainUiState> = _uiState.asStateFlow()

    init {
        checkAuthentication()
    }

    fun checkAuthentication() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(authState = AuthState.Loading)

            // Timeout the entire auth check — guarantees we ALWAYS leave Loading state.
            // Without this, a DataStore deadlock or network hang leaves the app on a
            // black screen permanently.
            try {
                withTimeout(13_000L) {
                    // DataStore .first() can deadlock if SessionManager.init's collect()
                    // holds the file lock. Wrap it with its own timeout as a safeguard.
                    val token = try {
                        withTimeout(3_000L) { authRepository.accessTokenFlow.first() }
                    } catch (_: Exception) {
                        // Fallback: read via the sync cache that SessionManager maintains
                        null
                    }

                    if (token.isNullOrBlank()) {
                        _uiState.value = _uiState.value.copy(authState = AuthState.Unauthenticated)
                        return@withTimeout
                    }

                    // Verify session with backend or offline cache (timeout after 10s)
                    val res = try {
                        withTimeout(10_000L) { authRepository.restoreSession() }
                    } catch (_: Exception) {
                        ApiResult.Error(code = 0, message = "Session restore timed out")
                    }
                    when (res) {
                        is ApiResult.Success -> {
                            val user = res.data
                            val role = Role.fromString(user.role)
                            val profile = authRepository.currentUserProfile.first()
                            _uiState.value = _uiState.value.copy(
                                authState = AuthState.Authenticated(role, profile)
                            )
                        }
                        is ApiResult.Error -> {
                            // Try to use cached profile if offline
                            val cached = authRepository.currentUserProfile.first()
                            if (cached != null) {
                                val role = Role.fromString(cached.role)
                                _uiState.value = _uiState.value.copy(
                                    authState = AuthState.Authenticated(role, cached)
                                )
                            } else {
                                authRepository.logout()
                                _uiState.value = _uiState.value.copy(authState = AuthState.Unauthenticated)
                            }
                        }
                        else -> {
                            _uiState.value = _uiState.value.copy(authState = AuthState.Unauthenticated)
                        }
                    }
                }
            } catch (_: Exception) {
                // Outer timeout expired or unexpected error — always show login screen,
                // never leave the user on a black/loading screen.
                _uiState.value = _uiState.value.copy(authState = AuthState.Unauthenticated)
            }
        }
    }


    fun onLoginSuccess(roleString: String) {
        viewModelScope.launch {
            val role = Role.fromString(roleString)
            val profile = authRepository.currentUserProfile.first()
            _uiState.value = _uiState.value.copy(
                authState = AuthState.Authenticated(role, profile),
                isPublicTraceActive = false
            )
        }
    }

    fun logout() {
        viewModelScope.launch {
            authRepository.logout()
            _uiState.value = _uiState.value.copy(
                authState = AuthState.Unauthenticated,
                isPublicTraceActive = false
            )
        }
    }

    fun setPublicTraceActive(active: Boolean) {
        _uiState.value = _uiState.value.copy(isPublicTraceActive = active)
    }
}
