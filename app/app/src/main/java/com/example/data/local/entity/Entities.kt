package com.example.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

enum class SyncState {
    PENDING,
    SYNCING,
    SYNCED,
    FAILED
}

@Entity(tableName = "user_profile")
data class UserProfileEntity(
    @PrimaryKey val id: String,
    val email: String,
    val fullName: String,
    val role: String,
    val phoneNumber: String? = null,
    val cachedAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "apiaries")
data class ApiaryEntity(
    @PrimaryKey val id: String,
    val name: String,
    val locationName: String? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
    val floraType: String? = null,
    val hiveCount: Int = 0,
    val syncState: SyncState = SyncState.SYNCED,
    val updatedAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "hives")
data class HiveEntity(
    @PrimaryKey val id: String,
    val apiaryId: String,
    val hiveNumber: String,
    val beeSpecies: String? = null,
    val installationDate: String? = null,
    val status: String = "ACTIVE",
    val healthScore: Int = 100,
    val syncState: SyncState = SyncState.SYNCED,
    val updatedAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "products")
data class ProductEntity(
    @PrimaryKey val id: String,
    val batchId: String,
    val title: String,
    val description: String? = null,
    val jarSizeGrams: Int = 500,
    val price: Double = 0.0,
    val traceToken: String,
    val status: String = "ANCHORED",
    val qrCodeUrl: String? = null,
    val isListed: Boolean = false,
    val syncState: SyncState = SyncState.SYNCED,
    val updatedAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "orders")
data class OrderEntity(
    @PrimaryKey val id: String,
    val buyerId: String? = null,
    val totalAmount: Double = 0.0,
    val status: String = "PENDING",
    val paymentStatus: String = "PENDING",
    val createdAt: String? = null,
    val itemsSummary: String = "",
    val syncState: SyncState = SyncState.SYNCED
)

@Entity(tableName = "alerts")
data class AlertEntity(
    @PrimaryKey val id: String,
    val hiveId: String,
    val alertType: String,
    val severity: String = "MEDIUM",
    val message: String,
    val isAcknowledged: Boolean = false,
    val isResolved: Boolean = false,
    val createdAt: String = ""
)

@Entity(tableName = "sync_queue")
data class SyncQueueEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val entityType: String, // "APIARY", "HIVE", "TELEMETRY"
    val payloadJson: String,
    val syncState: SyncState = SyncState.PENDING,
    val retryCount: Int = 0,
    val errorMessage: String? = null,
    val createdAt: Long = System.currentTimeMillis()
)
