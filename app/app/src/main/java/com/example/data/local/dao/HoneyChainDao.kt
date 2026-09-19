package com.example.data.local.dao

import androidx.room.*
import com.example.data.local.entity.*
import kotlinx.coroutines.flow.Flow

@Dao
interface HoneyChainDao {

    // User Profile
    @Query("SELECT * FROM user_profile LIMIT 1")
    fun getUserProfile(): Flow<UserProfileEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertUserProfile(user: UserProfileEntity)

    @Query("DELETE FROM user_profile")
    suspend fun clearUserProfile()

    // Apiaries
    @Query("SELECT * FROM apiaries ORDER BY updatedAt DESC")
    fun getAllApiaries(): Flow<List<ApiaryEntity>>

    @Query("SELECT * FROM apiaries WHERE id = :id LIMIT 1")
    suspend fun getApiaryById(id: String): ApiaryEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertApiaries(apiaries: List<ApiaryEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertApiary(apiary: ApiaryEntity)

    @Query("DELETE FROM apiaries WHERE id = :id")
    suspend fun deleteApiary(id: String)

    @Query("DELETE FROM apiaries")
    suspend fun clearApiaries()

    // Hives
    @Query("SELECT * FROM hives WHERE apiaryId = :apiaryId ORDER BY hiveCode ASC")
    fun getHivesByApiary(apiaryId: String): Flow<List<HiveEntity>>

    @Query("SELECT * FROM hives ORDER BY updatedAt DESC")
    fun getAllHives(): Flow<List<HiveEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertHives(hives: List<HiveEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertHive(hive: HiveEntity)

    @Query("DELETE FROM hives WHERE id = :id")
    suspend fun deleteHive(id: String)

    // Products
    @Query("SELECT * FROM products ORDER BY updatedAt DESC")
    fun getAllProducts(): Flow<List<ProductEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProducts(products: List<ProductEntity>)

    // Orders
    @Query("SELECT * FROM orders ORDER BY createdAt DESC")
    fun getAllOrders(): Flow<List<OrderEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOrders(orders: List<OrderEntity>)

    // Alerts
    @Query("SELECT * FROM alerts WHERE hiveId = :hiveId ORDER BY createdAt DESC")
    fun getAlertsByHive(hiveId: String): Flow<List<AlertEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAlerts(alerts: List<AlertEntity>)

    // Sync Queue
    @Query("SELECT * FROM sync_queue WHERE syncState = :state ORDER BY createdAt ASC")
    suspend fun getPendingSyncItems(state: SyncState = SyncState.PENDING): List<SyncQueueEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun enqueueSyncItem(item: SyncQueueEntity): Long

    @Update
    suspend fun updateSyncItem(item: SyncQueueEntity)

    @Query("DELETE FROM sync_queue WHERE id = :id")
    suspend fun removeSyncItem(id: Long)
}
