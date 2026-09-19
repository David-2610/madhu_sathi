package com.example.data.repository

import com.example.core.network.ApiResult
import com.example.core.network.NetworkErrorMapper
import com.example.data.local.dao.HoneyChainDao
import com.example.data.local.entity.ApiaryEntity
import com.example.data.local.entity.HiveEntity
import com.example.data.local.entity.SyncState
import com.example.data.remote.api.HoneyChainApiService
import com.example.data.remote.dto.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext

class BeekeeperRepository(
    private val apiService: HoneyChainApiService,
    private val dao: HoneyChainDao
) {

    val cachedApiaries: Flow<List<ApiaryEntity>> = dao.getAllApiaries()

    // Profile
    suspend fun getProfile(): ApiResult<BeekeeperProfileDto> = withContext(Dispatchers.IO) {
        try {
            val profile = apiService.getProfile()
            ApiResult.Success(profile)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun createProfile(profile: BeekeeperProfileDto): ApiResult<BeekeeperProfileDto> = withContext(Dispatchers.IO) {
        try {
            val result = apiService.createProfile(profile)
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun updateProfile(profile: BeekeeperProfileDto): ApiResult<BeekeeperProfileDto> = withContext(Dispatchers.IO) {
        try {
            val result = apiService.updateProfile(profile)
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    // Apiaries
    suspend fun fetchApiaries(skip: Int = 0, limit: Int = 50): ApiResult<List<ApiaryDto>> = withContext(Dispatchers.IO) {
        try {
            val apiaries = apiService.getApiaries(skip, limit)
            // Cache in Room
            val entities = apiaries.map {
                ApiaryEntity(
                    id = it.id,
                    name = it.name,
                    locationName = it.locationName,
                    latitude = it.latitude,
                    longitude = it.longitude,
                    floraType = it.floraType,
                    hiveCount = it.hiveCount ?: 0,
                    syncState = SyncState.SYNCED
                )
            }
            dao.insertApiaries(entities)
            ApiResult.Success(apiaries)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun createApiary(
        name: String,
        locationName: String?,
        latitude: Double?,
        longitude: Double?,
        floraType: String?
    ): ApiResult<ApiaryDto> = withContext(Dispatchers.IO) {
        try {
            val request = CreateApiaryRequest(name, locationName, latitude, longitude, floraType)
            val apiary = apiService.createApiary(request)
            dao.insertApiary(
                ApiaryEntity(
                    id = apiary.id,
                    name = apiary.name,
                    locationName = apiary.locationName,
                    latitude = apiary.latitude,
                    longitude = apiary.longitude,
                    floraType = apiary.floraType,
                    hiveCount = apiary.hiveCount ?: 0,
                    syncState = SyncState.SYNCED
                )
            )
            ApiResult.Success(apiary)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun deleteApiary(apiaryId: String): ApiResult<Unit> = withContext(Dispatchers.IO) {
        try {
            apiService.deleteApiary(apiaryId)
            dao.deleteApiary(apiaryId)
            ApiResult.Success(Unit)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    // Hives
    fun observeHivesForApiary(apiaryId: String): Flow<List<HiveEntity>> = dao.getHivesByApiary(apiaryId)

    suspend fun fetchHivesForApiary(apiaryId: String): ApiResult<List<HiveDto>> = withContext(Dispatchers.IO) {
        try {
            val hives = apiService.getHivesForApiary(apiaryId)
            val entities = hives.map {
                HiveEntity(
                    id = it.id,
                    apiaryId = it.apiaryId,
                    hiveCode = it.hiveCode,
                    hiveType = it.hiveType,
                    installationDate = it.installationDate,
                    status = it.status,
                    healthScore = it.healthScore ?: 100,
                    syncState = SyncState.SYNCED
                )
            }
            dao.insertHives(entities)
            ApiResult.Success(hives)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun createHive(
        apiaryId: String,
        hiveCode: String,
        hiveType: String,
        installationDate: String?,
        status: String = "ACTIVE"
    ): ApiResult<HiveDto> = withContext(Dispatchers.IO) {
        try {
            val request = CreateHiveRequest(hiveCode, hiveType, installationDate, status)
            val hive = apiService.createHive(apiaryId, request)
            dao.insertHive(
                HiveEntity(
                    id = hive.id,
                    apiaryId = hive.apiaryId,
                    hiveCode = hive.hiveCode,
                    hiveType = hive.hiveType,
                    installationDate = hive.installationDate,
                    status = hive.status,
                    healthScore = hive.healthScore ?: 100,
                    syncState = SyncState.SYNCED
                )
            )
            ApiResult.Success(hive)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun deleteHive(hiveId: String): ApiResult<Unit> = withContext(Dispatchers.IO) {
        try {
            apiService.deleteHive(hiveId)
            dao.deleteHive(hiveId)
            ApiResult.Success(Unit)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    // Harvests
    suspend fun fetchHarvests(hiveId: String): ApiResult<List<HarvestDto>> = withContext(Dispatchers.IO) {
        try {
            val list = apiService.getHarvestsForHive(hiveId)
            ApiResult.Success(list)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun createHarvest(
        hiveId: String,
        date: String,
        quantityKg: Double,
        moisturePct: Double?,
        flora: String?,
        notes: String?
    ): ApiResult<HarvestDto> = withContext(Dispatchers.IO) {
        try {
            val request = CreateHarvestRequest(date, quantityKg, moisturePct, flora, notes)
            val result = apiService.createHarvest(hiveId, request)
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    // Batches
    suspend fun fetchBatches(harvestId: String): ApiResult<List<BatchDto>> = withContext(Dispatchers.IO) {
        try {
            val list = apiService.getBatchesForHarvest(harvestId)
            ApiResult.Success(list)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun createBatch(
        harvestId: String,
        batchNumber: String,
        totalKg: Double,
        flora: String?,
        grade: String
    ): ApiResult<BatchDto> = withContext(Dispatchers.IO) {
        try {
            val request = CreateBatchRequest(batchNumber, totalKg, flora, grade)
            val result = apiService.createBatch(harvestId, request)
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    // Products
    suspend fun fetchProductsForBatch(batchId: String): ApiResult<List<ProductDto>> = withContext(Dispatchers.IO) {
        try {
            val list = apiService.getProductsForBatch(batchId)
            ApiResult.Success(list)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun createProduct(
        batchId: String,
        title: String,
        description: String?,
        jarSize: Int,
        price: Double
    ): ApiResult<ProductDto> = withContext(Dispatchers.IO) {
        try {
            val request = CreateProductRequest(title, description, jarSize, price)
            val result = apiService.createProduct(batchId, request)
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun addProductEvent(
        productId: String,
        eventType: String,
        eventTitle: String,
        description: String?,
        location: String?
    ): ApiResult<ProductEventDto> = withContext(Dispatchers.IO) {
        try {
            val request = CreateProductEventRequest(eventType, eventTitle, description, location)
            val result = apiService.addProductEvent(productId, request)
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun getProductQr(productId: String): ApiResult<QrResponseDto> = withContext(Dispatchers.IO) {
        try {
            val result = apiService.getProductQr(productId)
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun updateProductStatus(productId: String, status: String): ApiResult<ProductDto> = withContext(Dispatchers.IO) {
        try {
            val result = apiService.updateProductStatus(productId, UpdateProductStatusRequest(status))
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun updateListing(
        productId: String,
        isListed: Boolean,
        price: Double? = null,
        stock: Int? = null
    ): ApiResult<ProductListingDto> = withContext(Dispatchers.IO) {
        try {
            val result = apiService.updateProductListing(productId, UpdateListingRequest(isListed, price, stock))
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    // IoT & Health
    suspend fun submitTelemetry(
        hiveId: String,
        temperatureC: Double,
        humidityPct: Double,
        weightKg: Double,
        soundHz: Double? = null
    ): ApiResult<TelemetryResponseDto> = withContext(Dispatchers.IO) {
        try {
            val request = TelemetryRequest(temperatureC, humidityPct, weightKg, soundHz)
            val result = apiService.submitTelemetry(hiveId, request)
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun fetchAlerts(hiveId: String): ApiResult<List<HiveAlertDto>> = withContext(Dispatchers.IO) {
        try {
            val result = apiService.getHiveAlerts(hiveId)
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun acknowledgeAlert(alertId: String): ApiResult<HiveAlertDto> = withContext(Dispatchers.IO) {
        try {
            val result = apiService.acknowledgeAlert(alertId)
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun resolveAlert(alertId: String): ApiResult<HiveAlertDto> = withContext(Dispatchers.IO) {
        try {
            val result = apiService.resolveAlert(alertId)
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun getHiveHealth(hiveId: String): ApiResult<HiveHealthDto> = withContext(Dispatchers.IO) {
        try {
            val result = apiService.getHiveHealth(hiveId)
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun askAssistant(hiveId: String, question: String): ApiResult<AssistantResponseDto> = withContext(Dispatchers.IO) {
        try {
            val result = apiService.askHiveAssistant(hiveId, AssistantRequest(question))
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun runSimulator(hiveId: String): ApiResult<SimulationResultDto> = withContext(Dispatchers.IO) {
        try {
            val result = apiService.runSimulator(hiveId)
            ApiResult.Success(result)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }
}
