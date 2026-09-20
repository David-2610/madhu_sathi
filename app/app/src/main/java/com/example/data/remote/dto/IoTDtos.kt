package com.example.data.remote.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class HiveDeviceDto(
    @Json(name = "id") val id: String = "",
    @Json(name = "hive_id") val hiveId: String = "",
    @Json(name = "device_id") val deviceId: String = "",
    @Json(name = "device_type") val deviceType: String = "ESP32_SENSOR_NODE",
    @Json(name = "firmware_version") val firmwareVersion: String? = null,
    @Json(name = "is_active") val isActive: Boolean = true,
    @Json(name = "registered_at") val registeredAt: String? = null,
    @Json(name = "last_seen_at") val lastSeenAt: String? = null
) {
    val deviceSerial: String get() = deviceId
}

@JsonClass(generateAdapter = true)
data class RegisterDeviceRequest(
    @Json(name = "device_id") val deviceId: String,
    @Json(name = "device_type") val deviceType: String = "ESP32_SENSOR_NODE",
    @Json(name = "firmware_version") val firmwareVersion: String? = "1.0.0"
) {
    val deviceSerial: String get() = deviceId
}

@JsonClass(generateAdapter = true)
data class TelemetryRequest(
    @Json(name = "temperature_c") val temperatureC: Double,
    @Json(name = "humidity_percent") val humidityPercent: Double,
    @Json(name = "weight_kg") val weightKg: Double,
    @Json(name = "sound_level") val soundLevel: Double = 48.0,
    @Json(name = "vibration_level") val vibrationLevel: Double = 0.5,
    @Json(name = "battery_percent") val batteryPercent: Double? = 95.0,
    @Json(name = "device_id") val deviceId: String? = null,
    @Json(name = "timestamp") val timestamp: String? = null
) {
    val humidityPct: Double get() = humidityPercent
    val soundLevelDb: Double get() = soundLevel
    val soundFrequencyHz: Double? get() = soundLevel * 10.0
    val co2Ppm: Double? get() = 650.0
}

@JsonClass(generateAdapter = true)
data class TelemetryResponseDto(
    @Json(name = "id") val id: String? = null,
    @Json(name = "is_duplicate") val isDuplicate: Boolean = false,
    @Json(name = "message") val message: String? = null
)

@JsonClass(generateAdapter = true)
data class HiveAlertDto(
    @Json(name = "id") val id: String = "",
    @Json(name = "hive_id") val hiveId: String = "",
    @Json(name = "alert_type") val alertType: String = "HEALTH",
    @Json(name = "severity") val severity: String = "MEDIUM",
    @Json(name = "title") val title: String? = null,
    @Json(name = "message") val message: String = "",
    @Json(name = "is_acknowledged") val isAcknowledged: Boolean = false,
    @Json(name = "is_resolved") val isResolved: Boolean = false,
    @Json(name = "created_at") val createdAt: String? = null
)

@JsonClass(generateAdapter = true)
data class HiveHealthTelemetryDto(
    @Json(name = "id") val id: String? = null,
    @Json(name = "hive_id") val hiveId: String? = null,
    @Json(name = "temperature_c") val temperatureC: Double? = null,
    @Json(name = "humidity_percent") val humidityPercent: Double? = null,
    @Json(name = "weight_kg") val weightKg: Double? = null,
    @Json(name = "sound_level") val soundLevel: Double? = null,
    @Json(name = "vibration_level") val vibrationLevel: Double? = null,
    @Json(name = "battery_percent") val batteryPercent: Double? = null,
    @Json(name = "device_id") val deviceId: String? = null,
    @Json(name = "timestamp") val timestamp: String? = null
)

@JsonClass(generateAdapter = true)
data class HiveHealthMetricsDto(
    @Json(name = "latest_reading") val latestReading: HiveHealthTelemetryDto? = null,
    @Json(name = "avg_temperature_24h") val avgTemperature24h: Double? = null,
    @Json(name = "avg_humidity_24h") val avgHumidity24h: Double? = null,
    @Json(name = "weight_delta_24h") val weightDelta24h: Double? = null,
    @Json(name = "active_alerts_count") val activeAlertsCount: Int = 0,
    @Json(name = "last_seen_at") val lastSeenAt: String? = null
)

@JsonClass(generateAdapter = true)
data class HiveHealthDto(
    @Json(name = "hive_id") val hiveId: String = "",
    @Json(name = "hive_code") val hiveCode: String? = null,
    @Json(name = "health_status") val healthStatus: String? = null,
    @Json(name = "severity") val severity: String? = null,
    @Json(name = "summary") val summary: String? = null,
    @Json(name = "metrics") val metrics: HiveHealthMetricsDto? = null,
    @Json(name = "anomalies") val anomalies: List<String> = emptyList(),
    @Json(name = "active_alerts") val activeAlerts: List<HiveAlertDto> = emptyList(),
    @Json(name = "health_score") val healthScore: Int = 95,
    @Json(name = "temperature_c") val temperatureC: Double? = null,
    @Json(name = "humidity_pct") val humidityPct: Double? = null,
    @Json(name = "weight_kg") val weightKg: Double? = null,
    @Json(name = "sound_level_db") val soundLevelDb: Double? = null,
    @Json(name = "co2_ppm") val co2Ppm: Double? = null,
    @Json(name = "status") val status: String = "HEALTHY",
    @Json(name = "notes") val notes: String? = null
)

@JsonClass(generateAdapter = true)
data class AssistantRequest(
    @Json(name = "query") val query: String = ""
) {
    val question: String get() = query
}

@JsonClass(generateAdapter = true)
data class AssistantResponseDto(
    @Json(name = "hive_id") val hiveId: String? = null,
    @Json(name = "condition_summary") val conditionSummary: String? = null,
    @Json(name = "explanation") val explanation: String? = null,
    @Json(name = "recommended_steps") val recommendedSteps: List<String> = emptyList(),
    @Json(name = "disclaimer") val disclaimer: String? = null,
    @Json(name = "is_mock") val isMock: Boolean = false,
    @Json(name = "provider") val provider: String? = null,
    @Json(name = "answer") val answer: String = "Hive conditions are currently optimal.",
    @Json(name = "recommendations") val recommendations: List<String> = emptyList()
)

@JsonClass(generateAdapter = true)
data class SimulatorRunRequest(
    @Json(name = "scenario") val scenario: String = "NORMAL"
)

@JsonClass(generateAdapter = true)
data class SimulationResultDto(
    @Json(name = "status") val status: String = "SUCCESS",
    @Json(name = "message") val message: String = ""
)

@JsonClass(generateAdapter = true)
data class AiSummaryDto(
    @Json(name = "condition_summary") val conditionSummary: String,
    @Json(name = "explanation") val explanation: String,
    @Json(name = "recommended_steps") val recommendedSteps: List<String>
)
