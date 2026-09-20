package com.example.data.repository

import com.example.core.network.ApiResult
import com.example.data.remote.api.HoneyChainApiService
import com.example.data.remote.dto.KvicAlertDto
import com.example.data.remote.dto.KvicHiveDto
import com.example.data.remote.dto.KvicOverviewDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class AdminRepository(
    private val apiService: HoneyChainApiService
) {
    suspend fun getOverview(): ApiResult<KvicOverviewDto> = withContext(Dispatchers.IO) {
        kotlinx.coroutines.delay(500)
        ApiResult.Success(
            KvicOverviewDto(
                totalHives = 850,
                healthy = 700,
                warning = 100,
                critical = 50
            )
        )
    }

    suspend fun getHives(): ApiResult<List<KvicHiveDto>> = withContext(Dispatchers.IO) {
        kotlinx.coroutines.delay(500)
        ApiResult.Success(
            listOf(
                KvicHiveDto("hive_1", "NORMAL", 0, null),
                KvicHiveDto("hive_2", "WARNING", 1, null),
                KvicHiveDto("hive_3", "CRITICAL", 3, null)
            )
        )
    }

    suspend fun getAlerts(): ApiResult<List<KvicAlertDto>> = withContext(Dispatchers.IO) {
        kotlinx.coroutines.delay(500)
        ApiResult.Success(
            listOf(
                KvicAlertDto("alert_1", "hive_3", "HIGH", "Temperature reached 42°C", "2024-03-15T10:10:00Z"),
                KvicAlertDto("alert_2", "hive_2", "MEDIUM", "Humidity dropped to 45%", "2024-03-15T10:05:00Z")
            )
        )
    }
}
