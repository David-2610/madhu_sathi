package com.example.data.repository

import com.example.core.network.ApiResult
import com.example.core.network.NetworkErrorMapper
import com.example.data.remote.api.HoneyChainApiService
import com.example.data.remote.dto.QrResponseDto
import com.example.data.remote.dto.TraceabilityDetailDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class TraceabilityRepository(
    private val apiService: HoneyChainApiService
) {
    suspend fun getTraceability(traceToken: String): ApiResult<TraceabilityDetailDto> = withContext(Dispatchers.IO) {
        try {
            val details = apiService.getTraceability(traceToken.trim())
            ApiResult.Success(details)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun getTraceQr(traceToken: String): ApiResult<QrResponseDto> = withContext(Dispatchers.IO) {
        try {
            val qr = apiService.getTraceQr(traceToken.trim())
            ApiResult.Success(qr)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }
}
