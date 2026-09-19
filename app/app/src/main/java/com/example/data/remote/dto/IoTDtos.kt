package com.example.data.remote.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class HiveDeviceDto(
    @Json(name = "id") val id: String,
    @Json(name = "hive_id") val hiveId: String,
    @Json(name = "device_serial") val deviceSerial: String,
    @Json(name = "device_type") val deviceType: String = "TEMPERATURE_HUMIDITY",
    @Json(name = "is_active") val isActive: Boolean = true,
    @Json(name = "registered_at") val registeredAt: String? = null
)

@JsonClass(generateAdapter = true)
data class RegisterDeviceRequest(
    @Json(name = "device_serial") val deviceSerial: String,
    @Json(name = "device_type") val deviceType: String = "TEMPERATURE_HUMIDITY"
)

@JsonClass(generateAdapter = true)
data class TelemetryRequest(
    @Json(name = "temperature_c") val temperatureC: Double,
    @Json(name = "humidity_pct") val humidityPct: Double,
    @Json(name = "weight_kg") val weightKg: Double,
    @Json(name = "sound_frequency_hz") val soundFrequencyHz: Double? = null,
    @Json(name = "timestamp") val timestamp: String? = null
)

@JsonClass(generateAdapter = true)
data class TelemetryResponseDto(
    @Json(name = "id") val id: String? = null,
    @Json(name = "is_duplicate") val isDuplicate: Boolean = false,
    @Json(name = "message") val message: String? = null
)

@JsonClass(generateAdapter = true)
data class HiveAlertDto(
    @Json(name = "id") val id: String,
    @Json(name = "hive_id") val hiveId: String,
    @Json(name = "alert_type") val alertType: String,
    @Json(name = "severity") val severity: String = "MEDIUM",
    @Json(name = "message") val message: String,
    @Json(name = "is_acknowledged") val isAcknowledged: Boolean = false,
    @Json(name = "is_resolved") val isResolved: Boolean = false,
    @Json(name = "created_at") val createdAt: String? = null
)

@JsonClass(generateAdapter = true)
data class HiveHealthDto(
    @Json(name = "hive_id") val hiveId: String,
    @Json(name = "health_score") val healthScore: Int = 100,
    @Json(name = "temperature_c") val temperatureC: Double? = null,
    @Json(name = "humidity_pct") val humidityPct: Double? = null,
    @Json(name = "weight_kg") val weightKg: Double? = null,
    @Json(name = "status") val status: String = "NORMAL",
    @Json(name = "notes") val notes: String? = null
)

@JsonClass(generateAdapter = true)
data class AssistantRequest(
    @Json(name = "question") val question: String
)

@JsonClass(generateAdapter = true)
data class AssistantResponseDto(
    @Json(name = "answer") val answer: String,
    @Json(name = "recommendations") val recommendations: List<String> = emptyList()
)

@JsonClass(generateAdapter = true)
data class SimulationResultDto(
    @Json(name = "status") val status: String,
    @Json(name = "message") val message: String
)

@JsonClass(generateAdapter = true)
data class AiSummaryDto(
    @Json(name = "condition_summary") val conditionSummary: String,
    @Json(name = "explanation") val explanation: String,
    @Json(name = "recommended_steps") val recommendedSteps: List<String>
)
