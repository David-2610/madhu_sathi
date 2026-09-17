package com.example.data.remote.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class BeekeeperProfileDto(
    @Json(name = "id") val id: String? = null,
    @Json(name = "user_id") val userId: String? = null,
    @Json(name = "full_name") val fullName: String? = null,
    @Json(name = "phone_number") val phoneNumber: String? = null,
    @Json(name = "experience_years") val experienceYears: Int? = 0,
    @Json(name = "state") val state: String? = null,
    @Json(name = "district") val district: String? = null,
    @Json(name = "pincode") val pincode: String? = null,
    @Json(name = "address") val address: String? = null,
    @Json(name = "bio") val bio: String? = null,
    @Json(name = "certification_number") val certificationNumber: String? = null
)

@JsonClass(generateAdapter = true)
data class ApiaryDto(
    @Json(name = "id") val id: String,
    @Json(name = "name") val name: String,
    @Json(name = "location_name") val locationName: String? = null,
    @Json(name = "latitude") val latitude: Double? = null,
    @Json(name = "longitude") val longitude: Double? = null,
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
    @Json(name = "flora_type") val floraType: String? = null
)

@JsonClass(generateAdapter = true)
data class HiveDto(
    @Json(name = "id") val id: String,
    @Json(name = "apiary_id") val apiaryId: String,
    @Json(name = "hive_number") val hiveNumber: String,
    @Json(name = "bee_species") val beeSpecies: String? = null,
    @Json(name = "installation_date") val installationDate: String? = null,
    @Json(name = "status") val status: String = "ACTIVE",
    @Json(name = "health_score") val healthScore: Int? = 100
)

@JsonClass(generateAdapter = true)
data class CreateHiveRequest(
    @Json(name = "hive_number") val hiveNumber: String,
    @Json(name = "bee_species") val beeSpecies: String? = null,
    @Json(name = "installation_date") val installationDate: String? = null,
    @Json(name = "status") val status: String = "ACTIVE"
)

@JsonClass(generateAdapter = true)
data class HarvestDto(
    @Json(name = "id") val id: String,
    @Json(name = "hive_id") val hiveId: String,
    @Json(name = "harvest_date") val harvestDate: String,
    @Json(name = "quantity_kg") val quantityKg: Double,
    @Json(name = "moisture_percentage") val moisturePercentage: Double? = null,
    @Json(name = "floral_source") val floralSource: String? = null,
    @Json(name = "notes") val notes: String? = null
)

@JsonClass(generateAdapter = true)
data class CreateHarvestRequest(
    @Json(name = "harvest_date") val harvestDate: String,
    @Json(name = "quantity_kg") val quantityKg: Double,
    @Json(name = "moisture_percentage") val moisturePercentage: Double? = null,
    @Json(name = "floral_source") val floralSource: String? = null,
    @Json(name = "notes") val notes: String? = null
)

@JsonClass(generateAdapter = true)
data class BatchDto(
    @Json(name = "id") val id: String,
    @Json(name = "harvest_id") val harvestId: String,
    @Json(name = "batch_number") val batchNumber: String,
    @Json(name = "total_quantity_kg") val totalQuantityKg: Double,
    @Json(name = "floral_source") val floralSource: String? = null,
    @Json(name = "processing_date") val processingDate: String? = null,
    @Json(name = "quality_grade") val qualityGrade: String? = "A",
    @Json(name = "status") val status: String = "PENDING"
)

@JsonClass(generateAdapter = true)
data class CreateBatchRequest(
    @Json(name = "batch_number") val batchNumber: String,
    @Json(name = "total_quantity_kg") val totalQuantityKg: Double,
    @Json(name = "floral_source") val floralSource: String? = null,
    @Json(name = "quality_grade") val qualityGrade: String? = "A"
)
