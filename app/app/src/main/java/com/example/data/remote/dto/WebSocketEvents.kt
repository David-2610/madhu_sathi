package com.example.data.remote.dto

import com.squareup.moshi.JsonClass

sealed class WebSocketEvent {
    @JsonClass(generateAdapter = true)
    data class IotUpdate(
        val hiveId: String,
        val temperatureC: Double,
        val humidityPct: Double,
        val weightKg: Double,
        val healthScore: Int
    ) : WebSocketEvent()

    @JsonClass(generateAdapter = true)
    data class Alert(
        val hiveId: String,
        val alertId: String,
        val severity: String,
        val message: String
    ) : WebSocketEvent()

    @JsonClass(generateAdapter = true)
    data class AiAnalysis(
        val hiveId: String,
        val conditionSummary: String,
        val explanation: String,
        val recommendedSteps: List<String>
    ) : WebSocketEvent()

    @JsonClass(generateAdapter = true)
    data class InitialData(
        val message: String
    ) : WebSocketEvent()
}
