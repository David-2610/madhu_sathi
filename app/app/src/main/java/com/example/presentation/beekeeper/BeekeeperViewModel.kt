package com.example.presentation.beekeeper

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.core.network.ApiResult
import com.example.data.local.entity.ApiaryEntity
import com.example.data.remote.dto.*
import com.example.data.repository.BeekeeperRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.isActive
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

    // IoT Simulation & External IoT Server
    val iotServerUrl: String = "https://iotmockserver.vercel.app/",
    val isExternalIotConnected: Boolean = false,
    val externalIotStatus: String? = null,
    val isAutoStreaming: Boolean = false,
    val streamIntervalMs: Long = 2000L,
    val streamPacketCount: Int = 0,
    val selectedScenario: String = "HEALTHY",
    val currentTemp: Double = 34.8,
    val currentHumidity: Double = 58.0,
    val currentWeight: Double = 30.2,
    val currentSoundDb: Double = 48.0,
    val currentCo2Ppm: Double = 650.0,

    // Assistant
    val isAskingAssistant: Boolean = false,
    val chatMessages: List<ChatMessage> = emptyList(),
    
    // WebSocket
    val connectionState: com.example.core.network.WebSocketState = com.example.core.network.WebSocketState.DISCONNECTED,
    val aiSummary: AiSummaryDto? = null
)

class BeekeeperViewModel(
    private val beekeeperRepository: BeekeeperRepository,
    private val webSocketManager: com.example.core.network.WebSocketManager
) : ViewModel() {

    private val geminiChatService = com.example.domain.ai.GeminiChatService()

    private val _uiState = MutableStateFlow(BeekeeperUiState())
    val uiState: StateFlow<BeekeeperUiState> = _uiState.asStateFlow()

    init {
        loadProfile()
        loadApiaries()
        observeWebSocket()
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
        val selectedHiveId = _uiState.value.selectedHive?.id
        if (selectedHiveId == null) return

        when (event) {
            is WebSocketEvent.IotUpdate -> {
                if (event.hiveId == selectedHiveId) {
                    val currentHealth = _uiState.value.hiveHealth
                    val newHealth = currentHealth?.copy(
                        temperatureC = event.temperatureC,
                        humidityPct = event.humidityPct,
                        weightKg = event.weightKg,
                        healthScore = event.healthScore,
                        status = if (event.healthScore < 50) "CRITICAL" else if (event.healthScore < 80) "WARNING" else "NORMAL"
                    ) ?: HiveHealthDto(
                        hiveId = event.hiveId,
                        temperatureC = event.temperatureC,
                        humidityPct = event.humidityPct,
                        weightKg = event.weightKg,
                        healthScore = event.healthScore,
                        status = if (event.healthScore < 50) "CRITICAL" else if (event.healthScore < 80) "WARNING" else "NORMAL"
                    )
                    _uiState.value = _uiState.value.copy(hiveHealth = newHealth)
                }
            }
            is WebSocketEvent.Alert -> {
                if (event.hiveId == selectedHiveId) {
                    val newAlert = HiveAlertDto(
                        id = event.alertId,
                        hiveId = event.hiveId,
                        alertType = "REAL_TIME",
                        severity = event.severity,
                        message = event.message,
                        createdAt = "Just now"
                    )
                    _uiState.value = _uiState.value.copy(
                        alerts = listOf(newAlert) + _uiState.value.alerts
                    )
                }
            }
            is WebSocketEvent.AiAnalysis -> {
                if (event.hiveId == selectedHiveId) {
                    _uiState.value = _uiState.value.copy(
                        aiSummary = AiSummaryDto(
                            conditionSummary = event.conditionSummary,
                            explanation = event.explanation,
                            recommendedSteps = event.recommendedSteps
                        )
                    )
                }
            }
            is WebSocketEvent.InitialData -> {
                loadHiveHealth(selectedHiveId)
                loadAlerts(selectedHiveId)
            }
        }
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

    fun refreshData() {
        loadProfile()
        loadApiaries()
        _uiState.value.selectedHive?.let {
            loadHiveHealth(it.id)
            loadHarvests(it.id)
            loadAlerts(it.id)
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

    fun createHive(apiaryId: String, hiveCode: String, hiveType: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null, successMessage = null)
            when (val res = beekeeperRepository.createHive(apiaryId, hiveCode, hiveType, null)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        successMessage = "Hive $hiveCode added!"
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
        _uiState.value = _uiState.value.copy(selectedHive = hive, aiSummary = null)
        loadHiveHealth(hive.id)
        loadHarvests(hive.id)
        loadAlerts(hive.id)
        webSocketManager.connect()
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
                    val updatedList = _uiState.value.products.map {
                        if (it.id == productId) it.copy(isListed = isListed) else it
                    }
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        products = updatedList,
                        successMessage = if (isListed) "Product listed in public marketplace!" else "Product unlisted from marketplace"
                    )
                    _uiState.value.selectedBatch?.let { loadProductsForBatch(it.id) }
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = res.message)
                }
                else -> {
                    _uiState.value = _uiState.value.copy(isLoading = false)
                }
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

    private var autoStreamJob: Job? = null

    fun setIotServerUrl(url: String) {
        _uiState.value = _uiState.value.copy(iotServerUrl = url)
    }

    fun updateManualTelemetry(temp: Double, hum: Double, weight: Double, sound: Double, co2: Double) {
        _uiState.value = _uiState.value.copy(
            currentTemp = temp,
            currentHumidity = hum,
            currentWeight = weight,
            currentSoundDb = sound,
            currentCo2Ppm = co2,
            selectedScenario = "CUSTOM"
        )
    }

    fun applyPresetScenario(scenario: String, hiveId: String? = null) {
        val (temp, hum, weight, sound, co2) = when (scenario.uppercase()) {
            "HEALTHY" -> Quintuple(34.8, 58.0, 30.2, 48.0, 650.0)
            "OVERHEATING" -> Quintuple(39.4, 44.0, 29.1, 78.0, 980.0)
            "HUMIDITY" -> Quintuple(33.2, 85.0, 31.4, 52.0, 820.0)
            "SWARM" -> Quintuple(36.8, 52.0, 23.5, 96.0, 1280.0)
            "LOW_ACTIVITY" -> Quintuple(29.8, 65.0, 26.2, 25.0, 460.0)
            else -> Quintuple(34.8, 58.0, 30.2, 48.0, 650.0)
        }
        _uiState.value = _uiState.value.copy(
            selectedScenario = scenario,
            currentTemp = temp,
            currentHumidity = hum,
            currentWeight = weight,
            currentSoundDb = sound,
            currentCo2Ppm = co2
        )
        if (hiveId != null) {
            submitTelemetry(hiveId, temp, hum, weight, sound, co2)
            viewModelScope.launch {
                beekeeperRepository.setScenarioOnExternalIotServer(_uiState.value.iotServerUrl, hiveId, scenario)
            }
        }
    }

    fun submitTelemetry(
        hiveId: String,
        temp: Double = _uiState.value.currentTemp,
        humidity: Double = _uiState.value.currentHumidity,
        weight: Double = _uiState.value.currentWeight,
        soundDb: Double = _uiState.value.currentSoundDb,
        co2Ppm: Double = _uiState.value.currentCo2Ppm
    ) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isLoading = true,
                currentTemp = temp,
                currentHumidity = humidity,
                currentWeight = weight,
                currentSoundDb = soundDb,
                currentCo2Ppm = co2Ppm
            )

            // Compute immediate local health assessment to keep UI ultra responsive
            val score = calculateHealthScore(temp, humidity, weight, soundDb, co2Ppm)
            val status = when {
                score < 50 -> "CRITICAL"
                score < 80 -> "WARNING"
                else -> "NORMAL"
            }
            val localHealth = HiveHealthDto(
                hiveId = hiveId,
                healthScore = score,
                temperatureC = temp,
                humidityPct = humidity,
                weightKg = weight,
                soundLevelDb = soundDb,
                co2Ppm = co2Ppm,
                status = status,
                notes = "Real-time telemetry updated via IoT sensor link"
            )
            _uiState.value = _uiState.value.copy(hiveHealth = localHealth)

            when (val res = beekeeperRepository.submitTelemetry(
                hiveId = hiveId,
                temperatureC = temp,
                humidityPct = humidity,
                weightKg = weight,
                soundHz = soundDb * 10.0,
                soundLevelDb = soundDb,
                co2Ppm = co2Ppm
            )) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        successMessage = "Telemetry ingested: ${temp}°C, ${humidity}%, ${weight}kg, ${soundDb}dB, ${co2Ppm}ppm"
                    )
                    loadHiveHealth(hiveId)
                    loadAlerts(hiveId)
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        errorMessage = res.message
                    )
                }
                else -> {}
            }
        }
    }

    fun fetchFromExternalIotServer(hiveId: String = "") {
        viewModelScope.launch {
            val targetHive = hiveId.ifBlank {
                _uiState.value.selectedHive?.hiveCode ?: _uiState.value.selectedHive?.id ?: "1"
            }
            _uiState.value = _uiState.value.copy(
                isLoading = true,
                externalIotStatus = "Connecting to IoT Simulation Server for Hive $targetHive..."
            )
            when (val res = beekeeperRepository.fetchFromExternalIotServer(_uiState.value.iotServerUrl, targetHive)) {
                is ApiResult.Success -> {
                    val t = res.data
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        isExternalIotConnected = true,
                        externalIotStatus = "Synced Hive $targetHive from IoT Server",
                        currentTemp = t.temperatureC,
                        currentHumidity = t.humidityPct,
                        currentWeight = t.weightKg,
                        currentSoundDb = t.soundLevelDb ?: 48.0,
                        currentCo2Ppm = t.co2Ppm ?: 650.0,
                        successMessage = "Synced telemetry for Hive $targetHive from IoT Server!"
                    )
                    val backendHiveId = _uiState.value.selectedHive?.id ?: targetHive
                    submitTelemetry(
                        hiveId = backendHiveId,
                        temp = t.temperatureC,
                        humidity = t.humidityPct,
                        weight = t.weightKg,
                        soundDb = t.soundLevelDb ?: 48.0,
                        co2Ppm = t.co2Ppm ?: 650.0
                    )
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        isExternalIotConnected = false,
                        externalIotStatus = res.message,
                        errorMessage = res.message
                    )
                }
                else -> {}
            }
        }
    }

    fun startAutoStreaming(hiveId: String, intervalMs: Long = 2000L) {
        stopAutoStreaming()
        _uiState.value = _uiState.value.copy(
            isAutoStreaming = true,
            streamIntervalMs = intervalMs,
            streamPacketCount = 0
        )
        autoStreamJob = viewModelScope.launch {
            val targetHive = hiveId.ifBlank {
                _uiState.value.selectedHive?.hiveCode ?: _uiState.value.selectedHive?.id ?: "1"
            }
            while (isActive && _uiState.value.isAutoStreaming) {
                // Poll from external IoT Server
                val extRes = beekeeperRepository.fetchFromExternalIotServer(_uiState.value.iotServerUrl, targetHive)
                if (extRes is ApiResult.Success) {
                    val t = extRes.data
                    _uiState.value = _uiState.value.copy(
                        currentTemp = t.temperatureC,
                        currentHumidity = t.humidityPct,
                        currentWeight = t.weightKg,
                        currentSoundDb = t.soundLevelDb ?: 48.0,
                        currentCo2Ppm = t.co2Ppm ?: 650.0,
                        streamPacketCount = _uiState.value.streamPacketCount + 1,
                        isExternalIotConnected = true,
                        externalIotStatus = "Streaming live telemetry for Hive $targetHive"
                    )
                    val backendHiveId = _uiState.value.selectedHive?.id ?: targetHive
                    submitTelemetry(
                        hiveId = backendHiveId,
                        temp = t.temperatureC,
                        humidity = t.humidityPct,
                        weight = t.weightKg,
                        soundDb = t.soundLevelDb ?: 48.0,
                        co2Ppm = t.co2Ppm ?: 650.0
                    )
                } else {
                    val jitterTemp = (_uiState.value.currentTemp + ((-5..5).random() * 0.1)).coerceIn(15.0, 48.0)
                    val jitterHum = (_uiState.value.currentHumidity + ((-10..10).random() * 0.2)).coerceIn(20.0, 99.0)
                    val jitterWeight = (_uiState.value.currentWeight + ((-2..2).random() * 0.05)).coerceIn(5.0, 60.0)
                    val jitterSound = (_uiState.value.currentSoundDb + ((-15..15).random() * 0.2)).coerceIn(10.0, 110.0)
                    val jitterCo2 = (_uiState.value.currentCo2Ppm + ((-20..20).random() * 2.0)).coerceIn(300.0, 2500.0)

                    _uiState.value = _uiState.value.copy(
                        currentTemp = Math.round(jitterTemp * 10.0) / 10.0,
                        currentHumidity = Math.round(jitterHum * 10.0) / 10.0,
                        currentWeight = Math.round(jitterWeight * 100.0) / 100.0,
                        currentSoundDb = Math.round(jitterSound * 10.0) / 10.0,
                        currentCo2Ppm = Math.round(jitterCo2).toDouble(),
                        streamPacketCount = _uiState.value.streamPacketCount + 1
                    )

                    submitTelemetry(
                        hiveId = targetHive,
                        temp = _uiState.value.currentTemp,
                        humidity = _uiState.value.currentHumidity,
                        weight = _uiState.value.currentWeight,
                        soundDb = _uiState.value.currentSoundDb,
                        co2Ppm = _uiState.value.currentCo2Ppm
                    )
                }

                delay(intervalMs)
            }
        }
    }

    fun stopAutoStreaming() {
        autoStreamJob?.cancel()
        autoStreamJob = null
        _uiState.value = _uiState.value.copy(isAutoStreaming = false)
    }

    private fun calculateHealthScore(temp: Double, hum: Double, weight: Double, sound: Double, co2: Double): Int {
        var score = 100
        // Temp penalty (optimal 34.5 to 35.5)
        if (temp < 32.0 || temp > 38.0) score -= 30
        else if (temp < 34.0 || temp > 36.5) score -= 15

        // Humidity penalty (optimal 50 to 65%)
        if (hum < 40.0 || hum > 80.0) score -= 25
        else if (hum < 48.0 || hum > 70.0) score -= 10

        // Sound penalty (swarming > 85dB)
        if (sound > 85.0) score -= 35
        else if (sound < 30.0) score -= 15

        // CO2 penalty (>1000ppm)
        if (co2 > 1200.0) score -= 20
        else if (co2 > 900.0) score -= 10

        return score.coerceIn(10, 100)
    }

    override fun onCleared() {
        super.onCleared()
        stopAutoStreaming()
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

    fun askAssistant(question: String) {
        if (question.isBlank()) return
        
        viewModelScope.launch {
            // Add user message to UI immediately
            val userMsg = ChatMessage(role = "user", text = question)
            val currentMessages = _uiState.value.chatMessages.toMutableList()
            currentMessages.add(userMsg)
            _uiState.value = _uiState.value.copy(chatMessages = currentMessages, isAskingAssistant = true)

            // Send to Gemini
            val response = geminiChatService.sendMessage(question)
            
            // Add model response
            val modelMsg = ChatMessage(role = "model", text = response)
            currentMessages.add(modelMsg)
            _uiState.value = _uiState.value.copy(chatMessages = currentMessages, isAskingAssistant = false)
        }
    }

    fun analyzeTelemetryWithGemini() {
        val hive = _uiState.value.selectedHive
        val health = _uiState.value.hiveHealth
        val prompt = if (health != null) {
            "Analyze this current telemetry for Hive ${hive?.hiveCode ?: "Unknown"}: " +
            "Temp: ${health.temperatureC}°C, Humidity: ${health.humidityPct}%, " +
            "Weight: ${health.weightKg}kg, Sound: ${health.soundLevelDb}dB. " +
            "Provide a short diagnostic summary and any recommended actions."
        } else {
            "Analyze the telemetry for Hive ${hive?.hiveCode ?: "Unknown"}. Currently, temp is ${_uiState.value.currentTemp}°C, humidity is ${_uiState.value.currentHumidity}%, weight is ${_uiState.value.currentWeight}kg, and sound is ${_uiState.value.currentSoundDb}dB. Provide a concise diagnostic summary."
        }
        askAssistant(prompt)
    }

    fun clearChatHistory() {
        geminiChatService.resetChat()
        _uiState.value = _uiState.value.copy(chatMessages = emptyList())
    }

    fun clearMessages() {
        _uiState.value = _uiState.value.copy(errorMessage = null, successMessage = null)
    }

    fun clearProductQr() {
        _uiState.value = _uiState.value.copy(selectedProductQr = null)
    }
}

private data class Quintuple<A, B, C, D, E>(
    val first: A,
    val second: B,
    val third: C,
    val fourth: D,
    val fifth: E
)

data class ChatMessage(
    val role: String,
    val text: String
)
