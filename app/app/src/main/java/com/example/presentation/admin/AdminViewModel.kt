package com.example.presentation.admin

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.core.network.ApiResult
import com.example.data.remote.api.HoneyChainApiService
import com.example.data.remote.dto.*
import com.example.data.repository.TraceabilityRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AdminUiState(
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val successMessage: String? = null,
    val products: List<ProductDto> = emptyList(),
    val apiaries: List<ApiaryDto> = emptyList()
)

class AdminViewModel(
    private val apiService: HoneyChainApiService,
    private val traceabilityRepository: TraceabilityRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(AdminUiState())
    val uiState: StateFlow<AdminUiState> = _uiState.asStateFlow()

    init {
        loadAudits()
    }

    fun loadAudits() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
            try {
                // Fetch marketplace products to audit purity & compliance
                val products = apiService.getMarketplaceProducts()
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    products = products
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    errorMessage = e.localizedMessage ?: "Failed to load audit telemetry"
                )
            }
        }
    }

    fun updateProductStatus(productId: String, status: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                apiService.updateProductStatus(productId, UpdateProductStatusRequest(status = status))
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    successMessage = "Product status updated to $status"
                )
                loadAudits()
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    errorMessage = e.localizedMessage ?: "Failed to update product status"
                )
            }
        }
    }

    fun clearMessages() {
        _uiState.value = _uiState.value.copy(errorMessage = null, successMessage = null)
    }
}
