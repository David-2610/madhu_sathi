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
        try {
            val response = apiService.getKvicOverview()
            ApiResult.Success(response)
        } catch (e: Exception) {
            ApiResult.Error(message = e.localizedMessage ?: "Unknown error occurred")
        }
    }

    suspend fun getHives(): ApiResult<List<KvicHiveDto>> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.getKvicHives()
            ApiResult.Success(response)
        } catch (e: Exception) {
            ApiResult.Error(message = e.localizedMessage ?: "Unknown error occurred")
        }
    }

    suspend fun getAlerts(): ApiResult<List<KvicAlertDto>> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.getKvicAlerts()
            ApiResult.Success(response)
        } catch (e: Exception) {
            ApiResult.Error(message = e.localizedMessage ?: "Unknown error occurred")
        }
    }
}
