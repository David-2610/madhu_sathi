package com.example.data.remote.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class ProductDto(
    @Json(name = "id") val id: String,
    @Json(name = "batch_id") val batchId: String,
    @Json(name = "title") val title: String,
    @Json(name = "description") val description: String? = null,
    @Json(name = "jar_size_grams") val jarSizeGrams: Int = 500,
    @Json(name = "price") val price: Double = 0.0,
    @Json(name = "trace_token") val traceToken: String,
    @Json(name = "status") val status: String = "ANCHORED",
    @Json(name = "qr_code_url") val qrCodeUrl: String? = null,
    @Json(name = "is_listed") val isListed: Boolean = false,
    @Json(name = "created_at") val createdAt: String? = null
)

@JsonClass(generateAdapter = true)
data class CreateProductRequest(
    @Json(name = "title") val title: String,
    @Json(name = "description") val description: String? = null,
    @Json(name = "jar_size_grams") val jarSizeGrams: Int = 500,
    @Json(name = "price") val price: Double = 0.0
)

@JsonClass(generateAdapter = true)
data class ProductEventDto(
    @Json(name = "id") val id: String? = null,
    @Json(name = "product_id") val productId: String? = null,
    @Json(name = "event_type") val eventType: String,
    @Json(name = "event_title") val eventTitle: String,
    @Json(name = "description") val description: String? = null,
    @Json(name = "location") val location: String? = null,
    @Json(name = "timestamp") val timestamp: String? = null
)

@JsonClass(generateAdapter = true)
data class CreateProductEventRequest(
    @Json(name = "event_type") val eventType: String,
    @Json(name = "event_title") val eventTitle: String,
    @Json(name = "description") val description: String? = null,
    @Json(name = "location") val location: String? = null
)

@JsonClass(generateAdapter = true)
data class UpdateProductStatusRequest(
    @Json(name = "status") val status: String
)

@JsonClass(generateAdapter = true)
data class QrResponseDto(
    @Json(name = "qr_svg") val qrSvg: String? = null,
    @Json(name = "qr_url") val qrUrl: String? = null,
    @Json(name = "trace_token") val traceToken: String
)

@JsonClass(generateAdapter = true)
data class TraceabilityDetailDto(
    @Json(name = "trace_token") val traceToken: String,
    @Json(name = "product_title") val productTitle: String,
    @Json(name = "jar_size_grams") val jarSizeGrams: Int? = 500,
    @Json(name = "status") val status: String = "VERIFIED", // VERIFIED, SUSPICIOUS ACTIVITY, REVOKED, NOT FOUND, NOT YET ANCHORED
    @Json(name = "batch_number") val batchNumber: String? = null,
    @Json(name = "floral_source") val floralSource: String? = null,
    @Json(name = "harvest_date") val harvestDate: String? = null,
    @Json(name = "beekeeper_name") val beekeeperName: String? = null,
    @Json(name = "apiary_location") val apiaryLocation: String? = null,
    @Json(name = "quality_grade") val qualityGrade: String? = null,
    @Json(name = "moisture_percentage") val moisturePercentage: Double? = null,
    @Json(name = "batch_hash") val batchHash: String? = null,
    @Json(name = "events") val events: List<ProductEventDto> = emptyList()
)
