package com.example.presentation.beekeeper

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.core.network.ApiResult
import com.example.data.local.entity.ApiaryEntity
import com.example.data.remote.dto.*
import com.example.data.repository.BeekeeperRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

data class BeekeeperUiState(
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val successMessage: String? = null,

    // Profile
    val profile: BeekeeperProfileDto? = null,

    // Apiaries
    val apiaries: List<ApiaryDto> = emptyList(),
    val selectedApiary: ApiaryDto? = null,

    // Hives
    val hives: List<HiveDto> = emptyList(),
    val selectedHive: HiveDto? = null,

    // Harvests & Batches & Products
    val harvests: List<HarvestDto> = emptyList(),
    val selectedHarvest: HarvestDto? = null,
    val batches: List<BatchDto> = emptyList(),
    val selectedBatch: BatchDto? = null,
    val products: List<ProductDto> = emptyList(),
    val selectedProductQr: QrResponseDto? = null,

    // IoT & Alerts
    val alerts: List<HiveAlertDto> = emptyList(),
    val hiveHealth: HiveHealthDto? = null,
    val isSimulating: Boolean = false,

    // Assistant
    val assistantQuestion: String = "",
    val isAskingAssistant: Boolean = false,
    val assistantResponse: AssistantResponseDto? = null
)

class BeekeeperViewModel(
    private val beekeeperRepository: BeekeeperRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(BeekeeperUiState())
    val uiState: StateFlow<BeekeeperUiState> = _uiState.asStateFlow()

    init {
        loadProfile()
        loadApiaries()
    }

    fun loadProfile() {
        viewModelScope.launch {
            when (val res = beekeeperRepository.getProfile()) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(profile = res.data)
                is ApiResult.Error -> {}
                else -> {}
            }
        }
    }

    fun saveProfile(profile: BeekeeperProfileDto) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            val res = if (_uiState.value.profile == null) {
                beekeeperRepository.createProfile(profile)
            } else {
                beekeeperRepository.updateProfile(profile)
            }
            when (res) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        profile = res.data,
                        successMessage = "Profile updated successfully"
                    )
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = res.message)
                }
                else -> {}
            }
        }
    }

    fun loadApiaries() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
            when (val res = beekeeperRepository.fetchApiaries()) {
                is ApiResult.Success -> {
                    val apiaries = res.data
                    val selected = _uiState.value.selectedApiary ?: apiaries.firstOrNull()
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        apiaries = apiaries,
                        selectedApiary = selected
                    )
                    selected?.let { loadHivesForApiary(it.id) }
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = res.message)
                }
                else -> {}
            }
        }
    }

    fun createApiary(name: String, location: String?, flora: String?) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            when (val res = beekeeperRepository.createApiary(name, location, null, null, flora)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        successMessage = "Apiary '$name' registered!"
                    )
                    loadApiaries()
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = res.message)
                }
                else -> {}
            }
        }
    }

    fun selectApiary(apiary: ApiaryDto) {
        _uiState.value = _uiState.value.copy(selectedApiary = apiary)
        loadHivesForApiary(apiary.id)
    }

    fun loadHivesForApiary(apiaryId: String) {
        viewModelScope.launch {
            when (val res = beekeeperRepository.fetchHivesForApiary(apiaryId)) {
                is ApiResult.Success -> {
                    val hives = res.data
                    val selected = _uiState.value.selectedHive ?: hives.firstOrNull()
                    _uiState.value = _uiState.value.copy(
                        hives = hives,
                        selectedHive = selected
                    )
                    selected?.let {
                        loadHiveHealth(it.id)
                        loadHarvests(it.id)
                        loadAlerts(it.id)
                    }
                }
                is ApiResult.Error -> {}
                else -> {}
            }
        }
    }

    fun createHive(apiaryId: String, hiveNumber: String, species: String?) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            when (val res = beekeeperRepository.createHive(apiaryId, hiveNumber, species, null)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        successMessage = "Hive #$hiveNumber added!"
                    )
                    loadHivesForApiary(apiaryId)
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = res.message)
                }
                else -> {}
            }
        }
    }

    fun selectHive(hive: HiveDto) {
        _uiState.value = _uiState.value.copy(selectedHive = hive)
        loadHiveHealth(hive.id)
        loadHarvests(hive.id)
        loadAlerts(hive.id)
    }

    fun loadHarvests(hiveId: String) {
        viewModelScope.launch {
            when (val res = beekeeperRepository.fetchHarvests(hiveId)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        harvests = res.data,
                        selectedHarvest = res.data.firstOrNull()
                    )
                    res.data.firstOrNull()?.let { loadBatches(it.id) }
                }
                is ApiResult.Error -> {}
                else -> {}
            }
        }
    }

    fun createHarvest(
        hiveId: String,
        date: String,
        quantityKg: Double,
        moisturePct: Double?,
        flora: String?,
        notes: String?
    ) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            when (val res = beekeeperRepository.createHarvest(hiveId, date, quantityKg, moisturePct, flora, notes)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        successMessage = "Harvest recorded: ${quantityKg}kg"
                    )
                    loadHarvests(hiveId)
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = res.message)
                }
                else -> {}
            }
        }
    }

    fun loadBatches(harvestId: String) {
        viewModelScope.launch {
            when (val res = beekeeperRepository.fetchBatches(harvestId)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        batches = res.data,
                        selectedBatch = res.data.firstOrNull()
                    )
                    res.data.firstOrNull()?.let { loadProductsForBatch(it.id) }
                }
                is ApiResult.Error -> {}
                else -> {}
            }
        }
    }

    fun createBatch(harvestId: String, batchNumber: String, quantityKg: Double, flora: String?, grade: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            when (val res = beekeeperRepository.createBatch(harvestId, batchNumber, quantityKg, flora, grade)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        successMessage = "Batch $batchNumber created!"
                    )
                    loadBatches(harvestId)
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = res.message)
                }
                else -> {}
            }
        }
    }

    fun loadProductsForBatch(batchId: String) {
        viewModelScope.launch {
            when (val res = beekeeperRepository.fetchProductsForBatch(batchId)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(products = res.data)
                is ApiResult.Error -> {}
                else -> {}
            }
        }
    }

    fun createProduct(batchId: String, title: String, description: String?, jarSize: Int, price: Double) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            when (val res = beekeeperRepository.createProduct(batchId, title, description, jarSize, price)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        successMessage = "Product '$title' bottled & anchored!"
                    )
                    loadProductsForBatch(batchId)
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = res.message)
                }
                else -> {}
            }
        }
    }

    fun toggleProductListing(productId: String, isListed: Boolean, price: Double?) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            when (val res = beekeeperRepository.updateListing(productId, isListed, price)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        successMessage = if (isListed) "Product listed in public marketplace!" else "Product unlisted from marketplace"
                    )
                    _uiState.value.selectedBatch?.let { loadProductsForBatch(it.id) }
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = res.message)
                }
                else -> {}
            }
        }
    }

    fun loadProductQr(productId: String) {
        viewModelScope.launch {
            when (val res = beekeeperRepository.getProductQr(productId)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(selectedProductQr = res.data)
                is ApiResult.Error -> {}
                else -> {}
            }
        }
    }

    fun addProductEvent(productId: String, type: String, title: String, desc: String?, loc: String?) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            when (val res = beekeeperRepository.addProductEvent(productId, type, title, desc, loc)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        successMessage = "Event '$title' appended to product chain!"
                    )
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = res.message)
                }
                else -> {}
            }
        }
    }

    // IoT & Health
    fun loadHiveHealth(hiveId: String) {
        viewModelScope.launch {
            when (val res = beekeeperRepository.getHiveHealth(hiveId)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(hiveHealth = res.data)
                is ApiResult.Error -> {}
                else -> {}
            }
        }
    }

    fun loadAlerts(hiveId: String) {
        viewModelScope.launch {
            when (val res = beekeeperRepository.fetchAlerts(hiveId)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(alerts = res.data)
                is ApiResult.Error -> {}
                else -> {}
            }
        }
    }

    fun acknowledgeAlert(alertId: String, hiveId: String) {
        viewModelScope.launch {
            when (beekeeperRepository.acknowledgeAlert(alertId)) {
                is ApiResult.Success -> loadAlerts(hiveId)
                else -> {}
            }
        }
    }

    fun resolveAlert(alertId: String, hiveId: String) {
        viewModelScope.launch {
            when (beekeeperRepository.resolveAlert(alertId)) {
                is ApiResult.Success -> loadAlerts(hiveId)
                else -> {}
            }
        }
    }

    fun submitTelemetry(hiveId: String, temp: Double, humidity: Double, weight: Double) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            when (val res = beekeeperRepository.submitTelemetry(hiveId, temp, humidity, weight)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        successMessage = "Sensor telemetry ingested!"
                    )
                    loadHiveHealth(hiveId)
                    loadAlerts(hiveId)
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = res.message)
                }
                else -> {}
            }
        }
    }

    fun runSimulator(hiveId: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSimulating = true)
            when (val res = beekeeperRepository.runSimulator(hiveId)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isSimulating = false,
                        successMessage = "IoT simulator cycle completed: ${res.data.message}"
                    )
                    loadHiveHealth(hiveId)
                    loadAlerts(hiveId)
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isSimulating = false, errorMessage = res.message)
                }
                else -> {}
            }
        }
    }

    fun askAssistant(hiveId: String, question: String) {
        if (question.isBlank()) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isAskingAssistant = true)
            when (val res = beekeeperRepository.askAssistant(hiveId, question)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isAskingAssistant = false,
                        assistantResponse = res.data
                    )
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isAskingAssistant = false,
                        errorMessage = res.message
                    )
                }
                else -> {}
            }
        }
    }

    fun clearMessages() {
        _uiState.value = _uiState.value.copy(errorMessage = null, successMessage = null)
    }

    fun clearProductQr() {
        _uiState.value = _uiState.value.copy(selectedProductQr = null)
    }
}
