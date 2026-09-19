package com.example.presentation.admin

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.core.network.ApiResult
import com.example.core.network.WebSocketManager
import com.example.core.network.WebSocketState
import com.example.data.remote.dto.*
import com.example.data.repository.AdminRepository
import com.example.data.repository.TraceabilityRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

data class AdminUiState(
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val connectionState: WebSocketState = WebSocketState.DISCONNECTED,
    val overview: KvicOverviewDto? = null,
    val hives: List<KvicHiveDto> = emptyList(),
    val alerts: List<KvicAlertDto> = emptyList()
)

class AdminViewModel(
    private val adminRepository: AdminRepository,
    private val traceabilityRepository: TraceabilityRepository,
    private val webSocketManager: WebSocketManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(AdminUiState())
    val uiState: StateFlow<AdminUiState> = _uiState.asStateFlow()

    init {
        loadDashboardData()
        observeWebSocket()
    }

    fun loadDashboardData() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
            
            val overviewResult = adminRepository.getOverview()
            val hivesResult = adminRepository.getHives()
            val alertsResult = adminRepository.getAlerts()

            val overview = if (overviewResult is ApiResult.Success) overviewResult.data else null
            val hives = if (hivesResult is ApiResult.Success) hivesResult.data else emptyList()
            val alerts = if (alertsResult is ApiResult.Success) alertsResult.data else emptyList()

            _uiState.value = _uiState.value.copy(
                isLoading = false,
                overview = overview,
                hives = hives,
                alerts = alerts
            )

            // Connect to WebSocket after initial load
            webSocketManager.connect()
        }
    }

    private fun observeWebSocket() {
        viewModelScope.launch {
            webSocketManager.connectionState.collect { state ->
                _uiState.value = _uiState.value.copy(connectionState = state)
            }
        }

        viewModelScope.launch {
            webSocketManager.events.collect { event ->
                handleWebSocketEvent(event)
            }
        }
    }

    private fun handleWebSocketEvent(event: WebSocketEvent) {
        when (event) {
            is WebSocketEvent.Alert -> {
                val newAlert = KvicAlertDto(
                    alertId = event.alertId,
                    hiveId = event.hiveId,
                    severity = event.severity,
                    message = event.message,
                    timestamp = "Just now"
                )
                _uiState.value = _uiState.value.copy(
                    alerts = listOf(newAlert) + _uiState.value.alerts,
                    overview = _uiState.value.overview?.copy(
                        warning = _uiState.value.overview?.warning?.plus(if (event.severity == "WARNING") 1 else 0) ?: 0,
                        critical = _uiState.value.overview?.critical?.plus(if (event.severity == "CRITICAL") 1 else 0) ?: 0
                    )
                )
            }
            is WebSocketEvent.AiAnalysis -> {
                val updatedHives = _uiState.value.hives.map { hive ->
                    if (hive.hiveId == event.hiveId) {
                        hive.copy(
                            aiSummary = AiSummaryDto(
                                conditionSummary = event.conditionSummary,
                                explanation = event.explanation,
                                recommendedSteps = event.recommendedSteps
                            )
                        )
                    } else hive
                }
                _uiState.value = _uiState.value.copy(hives = updatedHives)
            }
            is WebSocketEvent.IotUpdate -> {
                // Update hive status based on health score if needed, or update overview stats
            }
            is WebSocketEvent.InitialData -> {
                // Handled if we need a full refresh
                loadDashboardData()
            }
        }
    }

    fun clearMessages() {
        _uiState.value = _uiState.value.copy(errorMessage = null)
    }
}
