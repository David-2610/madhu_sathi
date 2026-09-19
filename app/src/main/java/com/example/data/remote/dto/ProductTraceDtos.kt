package com.example.data.remote.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class ProductDto(
    @Json(name = "id") val id: String = "",
    @Json(name = "batch_id") val batchId: String? = null,
    @Json(name = "serial_number") val serialNumber: String = "",
    @Json(name = "trace_token") val traceTokenField: String? = null,
    @Json(name = "net_weight_g") val netWeightG: Double? = 500.0,
    @Json(name = "packaging_date") val packagingDate: String? = null,
    @Json(name = "expiry_date") val expiryDate: String? = null,
    @Json(name = "status") val statusField: String? = null,
    @Json(name = "trace_url") val traceUrl: String? = null,
    @Json(name = "qr_code_svg") val qrCodeSvg: String? = null,
    @Json(name = "title") val titleField: String? = null,
    @Json(name = "description") val descriptionField: String? = null,
    @Json(name = "price") val priceString: String? = null,
    @Json(name = "currency") val currency: String? = "INR",
    @Json(name = "is_available") val isAvailable: Boolean? = true,
    @Json(name = "is_listed") val isListed: Boolean? = true,
    @Json(name = "batch_code") val batchCode: String? = null,
    @Json(name = "apiary_name") val apiaryName: String? = null,
    @Json(name = "district") val district: String? = null,
    @Json(name = "state") val state: String? = null,
    @Json(name = "beekeeper_code") val beekeeperCode: String? = null,
    @Json(name = "honey_type") val honeyType: String? = null,
    @Json(name = "batch_date") val batchDate: String? = null,
    @Json(name = "harvest_date") val harvestDate: String? = null,
    @Json(name = "created_at") val createdAt: String? = null
) {
    val title: String get() = titleField ?: (if (!honeyType.isNullOrBlank()) "$honeyType Honey (${jarSizeGrams}g)" else serialNumber.ifBlank { "Honey Jar (${jarSizeGrams}g)" })
    val description: String get() = descriptionField ?: "Pure ${honeyType ?: "Raw Forest"} Honey from ${apiaryName ?: "Certified Apiary"}${if (!district.isNullOrBlank()) ", $district" else ""}. Batch ${batchCode ?: "Verified"}."
    val jarSizeGrams: Int get() = netWeightG?.toInt() ?: 500
    val price: Double get() = priceString?.toDoubleOrNull() ?: 450.0
    val status: String get() = statusField ?: if (isAvailable == true) "AVAILABLE" else "OUT_OF_STOCK"
    val traceToken: String get() = traceTokenField ?: (traceUrl?.substringAfterLast("/") ?: serialNumber)
    val qrCodeUrl: String? get() = traceUrl
}

@JsonClass(generateAdapter = true)
data class CreateProductRequest(
    @Json(name = "net_weight_g") val netWeightG: Double = 500.0,
    @Json(name = "packaging_date") val packagingDate: String,
    @Json(name = "expiry_date") val expiryDate: String? = null,
    @Json(name = "serial_number") val serialNumber: String? = null
)

@JsonClass(generateAdapter = true)
data class ProductEventDto(
    @Json(name = "id") val id: String? = null,
    @Json(name = "product_id") val productId: String? = null,
    @Json(name = "event_type") val eventType: String = "VERIFIED",
    @Json(name = "event_title") val eventTitleField: String? = null,
    @Json(name = "description") val description: String? = null,
    @Json(name = "location") val location: String? = null,
    @Json(name = "timestamp") val timestampField: String? = null,
    @Json(name = "event_date") val eventDate: String? = null,
    @Json(name = "event_hash") val eventHash: String? = null,
    @Json(name = "is_on_chain") val isOnChain: Boolean? = true
) {
    val eventTitle: String get() = eventTitleField ?: eventType.replace("_", " ").lowercase().replaceFirstChar { it.uppercase() }
    val timestamp: String? get() = timestampField ?: eventDate
}

@JsonClass(generateAdapter = true)
data class CreateProductEventRequest(
    @Json(name = "event_type") val eventType: String,
    @Json(name = "description") val description: String,
    @Json(name = "location") val location: String? = null,
    @Json(name = "metadata") val metadata: Map<String, String>? = null
)

@JsonClass(generateAdapter = true)
data class UpdateProductStatusRequest(
    @Json(name = "status") val status: String
)

@JsonClass(generateAdapter = true)
data class QrResponseDto(
    @Json(name = "qr_code_svg") val qrSvgBackend: String? = null,
    @Json(name = "qr_svg") val qrSvg: String? = null,
    @Json(name = "qr_url") val qrUrl: String? = null,
    @Json(name = "trace_url") val traceUrl: String? = null,
    @Json(name = "trace_token") val traceToken: String = ""
) {
    val svgData: String? get() = qrSvgBackend ?: qrSvg
    val targetUrl: String? get() = qrUrl ?: traceUrl
}

@JsonClass(generateAdapter = true)
data class SafeBatchInfo(
    @Json(name = "batch_code") val batchCode: String = "",
    @Json(name = "batch_date") val batchDate: String = ""
)

@JsonClass(generateAdapter = true)
data class SafeHarvestInfo(
    @Json(name = "harvest_date") val harvestDate: String = "",
    @Json(name = "honey_type") val honeyType: String = ""
)

@JsonClass(generateAdapter = true)
data class SafeOriginInfo(
    @Json(name = "apiary_name") val apiaryName: String = "",
    @Json(name = "village") val village: String? = null,
    @Json(name = "district") val district: String? = null,
    @Json(name = "state") val state: String? = null
)

@JsonClass(generateAdapter = true)
data class SafeBeekeeperInfo(
    @Json(name = "beekeeper_code") val beekeeperCode: String = "",
    @Json(name = "experience_years") val experienceYears: Int? = null
)

@JsonClass(generateAdapter = true)
data class BlockchainVerificationInfo(
    @Json(name = "is_on_chain") val isOnChain: Boolean = false,
    @Json(name = "network") val network: String = "Algorand/Polygon Testnet",
    @Json(name = "latest_event_hash") val latestEventHash: String = "",
    @Json(name = "verification_status") val verificationStatus: String = "VERIFIED"
)

@JsonClass(generateAdapter = true)
data class TraceabilityDetailDto(
    @Json(name = "serial_number") val serialNumber: String = "",
    @Json(name = "status") val statusVal: String = "VERIFIED",
    @Json(name = "is_valid") val isValid: Boolean = true,
    @Json(name = "honey_type") val honeyType: String? = null,
    @Json(name = "net_weight_g") val netWeightG: Double? = 500.0,
    @Json(name = "packaging_date") val packagingDate: String? = null,
    @Json(name = "expiry_date") val expiryDate: String? = null,
    @Json(name = "batch") val batch: SafeBatchInfo? = null,
    @Json(name = "harvest") val harvest: SafeHarvestInfo? = null,
    @Json(name = "origin") val origin: SafeOriginInfo? = null,
    @Json(name = "beekeeper") val beekeeper: SafeBeekeeperInfo? = null,
    @Json(name = "timeline") val timeline: List<ProductEventDto> = emptyList(),
    @Json(name = "blockchain_verification") val blockchainVerification: BlockchainVerificationInfo? = null,
    @Json(name = "trace_token") val tokenField: String? = null,
    @Json(name = "product_title") val productTitleField: String? = null
) {
    val traceToken: String get() = tokenField ?: serialNumber
    val productTitle: String get() = productTitleField ?: ("Pure " + (honeyType ?: "Multiflora Honey"))
    val jarSizeGrams: Int? get() = netWeightG?.toInt() ?: 500
    val status: String get() = if (isValid) (statusVal.ifBlank { "VERIFIED" }) else "SUSPICIOUS ACTIVITY"
    val batchNumber: String? get() = batch?.batchCode
    val floralSource: String? get() = honeyType ?: harvest?.honeyType
    val harvestDate: String? get() = harvest?.harvestDate
    val beekeeperName: String? get() = beekeeper?.beekeeperCode
    val apiaryLocation: String? get() = listOfNotNull(origin?.apiaryName, origin?.village, origin?.district, origin?.state).joinToString(", ").ifBlank { null }
    val qualityGrade: String? get() = "A"
    val moisturePercentage: Double? get() = 17.5
    val batchHash: String? get() = blockchainVerification?.latestEventHash
    val events: List<ProductEventDto> get() = timeline
}
