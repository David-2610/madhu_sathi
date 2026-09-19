package com.example.data.remote.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class KvicOverviewDto(
    @Json(name = "totalHives") val totalHives: Int,
    @Json(name = "healthy") val healthy: Int,
    @Json(name = "warning") val warning: Int,
    @Json(name = "critical") val critical: Int
)

@JsonClass(generateAdapter = true)
data class KvicHiveDto(
    @Json(name = "hiveId") val hiveId: String,
    @Json(name = "status") val status: String,
    @Json(name = "alertsCount") val alertsCount: Int,
    @Json(name = "aiSummary") val aiSummary: AiSummaryDto? = null
)

@JsonClass(generateAdapter = true)
data class KvicAlertDto(
    @Json(name = "alertId") val alertId: String,
    @Json(name = "hiveId") val hiveId: String,
    @Json(name = "severity") val severity: String,
    @Json(name = "message") val message: String,
    @Json(name = "timestamp") val timestamp: String
)
