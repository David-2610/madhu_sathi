package com.example.presentation.trace

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.core.network.ApiResult
import com.example.data.remote.dto.TraceabilityDetailDto
import com.example.data.repository.TraceabilityRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class TraceUiState(
    val isLoading: Boolean = false,
    val traceDetails: TraceabilityDetailDto? = null,
    val errorMessage: String? = null,
    val searchedToken: String = ""
)

class TraceViewModel(
    private val traceabilityRepository: TraceabilityRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(TraceUiState())
    val uiState: StateFlow<TraceUiState> = _uiState.asStateFlow()

    fun searchTrace(token: String) {
        val trimmed = token.trim()
        if (trimmed.isBlank()) return

        viewModelScope.launch {
            _uiState.value = TraceUiState(isLoading = true, searchedToken = trimmed)
            when (val res = traceabilityRepository.getTraceability(trimmed)) {
                is ApiResult.Success -> {
                    _uiState.value = TraceUiState(traceDetails = res.data, searchedToken = trimmed)
                }
                is ApiResult.Error -> {
                    _uiState.value = TraceUiState(
                        errorMessage = res.message,
                        searchedToken = trimmed
                    )
                }
                else -> {}
            }
        }
    }

    fun clear() {
        _uiState.value = TraceUiState()
    }
}
