package com.example.presentation.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.core.network.ApiResult
import com.example.data.repository.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AuthUiState(
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val fieldErrors: Map<String, String> = emptyMap(),
    val isSuccess: Boolean = false
)

class AuthViewModel(
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    fun login(
        email: String,
        pass: String,
        onSuccess: (role: String) -> Unit
    ) {
        val emailTrimmed = email.trim()
        val errors = mutableMapOf<String, String>()

        if (emailTrimmed.isBlank() || !android.util.Patterns.EMAIL_ADDRESS.matcher(emailTrimmed).matches()) {
            errors["email"] = "Please enter a valid email address"
        }
        if (pass.isBlank() || pass.length < 6) {
            errors["password"] = "Password must be at least 6 characters"
        }

        if (errors.isNotEmpty()) {
            _uiState.value = AuthUiState(fieldErrors = errors)
            return
        }

        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            when (val res = authRepository.login(emailTrimmed, pass)) {
                is ApiResult.Success -> {
                    _uiState.value = AuthUiState(isSuccess = true)
                    onSuccess(res.data.role)
                }
                is ApiResult.Error -> {
                    _uiState.value = AuthUiState(
                        errorMessage = res.message,
                        fieldErrors = res.fieldErrors
                    )
                }
                else -> {}
            }
        }
    }

    fun register(
        email: String,
        pass: String,
        fullName: String,
        role: String,
        phone: String,
        onSuccess: () -> Unit
    ) {
        val emailTrimmed = email.trim()
        val nameTrimmed = fullName.trim()
        val errors = mutableMapOf<String, String>()

        if (emailTrimmed.isBlank() || !android.util.Patterns.EMAIL_ADDRESS.matcher(emailTrimmed).matches()) {
            errors["email"] = "Please enter a valid email address"
        }
        if (pass.isBlank() || pass.length < 6) {
            errors["password"] = "Password must be at least 6 characters"
        }
        if (nameTrimmed.isBlank()) {
            errors["fullName"] = "Please enter your full name"
        }
        val phoneTrimmed = phone.trim()
        if (phoneTrimmed.isBlank() || !phoneTrimmed.matches(Regex("^\\d{10}$"))) {
            errors["phone"] = "Phone number must be exactly 10 digits"
        }

        if (errors.isNotEmpty()) {
            _uiState.value = AuthUiState(fieldErrors = errors)
            return
        }

        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            when (val res = authRepository.register(emailTrimmed, pass, nameTrimmed, role, phoneTrimmed)) {
                is ApiResult.Success -> {
                    _uiState.value = AuthUiState(isSuccess = true)
                    onSuccess()
                }
                is ApiResult.Error -> {
                    _uiState.value = AuthUiState(
                        errorMessage = res.message,
                        fieldErrors = res.fieldErrors
                    )
                }
                else -> {}
            }
        }
    }



    fun clearErrors() {
        _uiState.value = _uiState.value.copy(errorMessage = null, fieldErrors = emptyMap())
    }
}
