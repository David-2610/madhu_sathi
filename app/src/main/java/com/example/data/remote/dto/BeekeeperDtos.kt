package com.example.data.remote.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class BeekeeperProfileDto(
    @Json(name = "id") val id: String? = null,
    @Json(name = "user_id") val userId: String? = null,
    @Json(name = "beekeeper_code") val beekeeperCode: String? = null,
    @Json(name = "full_name") val fullName: String? = null,
    @Json(name = "phone") val phoneNumber: String? = null,
    @Json(name = "experience_years") val experienceYears: Int? = 0,
    @Json(name = "state") val state: String? = null,
    @Json(name = "district") val district: String? = null,
    @Json(name = "village") val village: String? = null,
    @Json(name = "pincode") val pincode: String? = null,
    @Json(name = "address") val address: String? = null,
    @Json(name = "bio") val bio: String? = null,
    @Json(name = "certification_number") val certificationNumber: String? = null,
    @Json(name = "created_at") val createdAt: String? = null
)

@JsonClass(generateAdapter = true)
data class BeekeeperProfileCreate(
    @Json(name = "beekeeper_code") val beekeeperCode: String? = null,
    @Json(name = "address") val address: String? = null,
    @Json(name = "village") val village: String? = null,
    @Json(name = "district") val district: String? = null,
    @Json(name = "state") val state: String? = null,
    @Json(name = "pincode") val pincode: String? = null,
    @Json(name = "experience_years") val experienceYears: Int? = null
)

@JsonClass(generateAdapter = true)
data class ApiaryDto(
    @Json(name = "id") val id: String,
    @Json(name = "name") val name: String,
    @Json(name = "location_name") val locationName: String? = null,
    @Json(name = "latitude") val latitude: Double? = null,
    @Json(name = "longitude") val longitude: Double? = null,
    @Json(name = "address") val address: String? = null,
    @Json(name = "flora_type") val floraType: String? = null,
    @Json(name = "hive_count") val hiveCount: Int? = 0,
    @Json(name = "created_at") val createdAt: String? = null
)

@JsonClass(generateAdapter = true)
data class CreateApiaryRequest(
    @Json(name = "name") val name: String,
    @Json(name = "location_name") val locationName: String? = null,
    @Json(name = "latitude") val latitude: Double? = null,
    @Json(name = "longitude") val longitude: Double? = null,
    @Json(name = "address") val address: String? = null,
    @Json(name = "flora_type") val floraType: String? = null
)

@JsonClass(generateAdapter = true)
data class HiveDto(
    @Json(name = "id") val id: String,
    @Json(name = "apiary_id") val apiaryId: String,
    @Json(name = "hive_code") val hiveCode: String,
    @Json(name = "hive_type") val hiveType: String? = null,
    @Json(name = "installation_date") val installationDate: String? = null,
    @Json(name = "status") val status: String = "ACTIVE",
    @Json(name = "health_score") val healthScore: Int? = 100
)

@JsonClass(generateAdapter = true)
data class CreateHiveRequest(
    @Json(name = "hive_code") val hiveCode: String,
    @Json(name = "hive_type") val hiveType: String,
    @Json(name = "installation_date") val installationDate: String? = null,
    @Json(name = "status") val status: String = "ACTIVE"
)

@JsonClass(generateAdapter = true)
data class HarvestDto(
    @Json(name = "id") val id: String,
    @Json(name = "hive_id") val hiveId: String,
    @Json(name = "harvest_date") val harvestDate: String,
    @Json(name = "actual_quantity_kg") val actualQuantityKg: Double = 0.0,
    @Json(name = "estimated_quantity_kg") val estimatedQuantityKg: Double? = null,
    @Json(name = "honey_type") val honeyType: String = "Multiflora Honey",
    @Json(name = "notes") val notes: String? = null,
    @Json(name = "created_at") val createdAt: String? = null,
    @Json(name = "updated_at") val updatedAt: String? = null
) {
    val quantityKg: Double get() = actualQuantityKg
    val floralSource: String get() = honeyType
    val moisturePercentage: Double? get() = null
}

@JsonClass(generateAdapter = true)
data class CreateHarvestRequest(
    @Json(name = "harvest_date") val harvestDate: String,
    @Json(name = "actual_quantity_kg") val actualQuantityKg: Double,
    @Json(name = "honey_type") val honeyType: String,
    @Json(name = "estimated_quantity_kg") val estimatedQuantityKg: Double? = null,
    @Json(name = "notes") val notes: String? = null
)

@JsonClass(generateAdapter = true)
data class BatchDto(
    @Json(name = "id") val id: String,
    @Json(name = "harvest_id") val harvestId: String,
    @Json(name = "beekeeper_id") val beekeeperId: String? = null,
    @Json(name = "batch_code") val batchCode: String = "",
    @Json(name = "batch_date") val batchDate: String? = null,
    @Json(name = "quantity_kg") val quantityKg: Double = 0.0,
    @Json(name = "honey_type") val honeyType: String = "Multiflora Honey",
    @Json(name = "status") val status: String = "CREATED",
    @Json(name = "created_at") val createdAt: String? = null
) {
    val batchNumber: String get() = batchCode
    val totalQuantityKg: Double get() = quantityKg
    val floralSource: String get() = honeyType
    val processingDate: String? get() = batchDate
    val qualityGrade: String get() = "Grade A"
}

@JsonClass(generateAdapter = true)
data class CreateBatchRequest(
    @Json(name = "batch_code") val batchCode: String,
    @Json(name = "batch_date") val batchDate: String,
    @Json(name = "quantity_kg") val quantityKg: Double,
    @Json(name = "honey_type") val honeyType: String,
    @Json(name = "status") val status: String = "CREATED"
)
