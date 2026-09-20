package com.example.data.local.database

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverter
import androidx.room.TypeConverters
import com.example.data.local.dao.HoneyChainDao
import com.example.data.local.entity.*

class Converters {
    @TypeConverter
    fun fromSyncState(state: SyncState): String = state.name

    @TypeConverter
    fun toSyncState(value: String): SyncState = try {
        SyncState.valueOf(value)
    } catch (_: Exception) {
        SyncState.SYNCED
    }
}

@Database(
    entities = [
        UserProfileEntity::class,
        ApiaryEntity::class,
        HiveEntity::class,
        ProductEntity::class,
        OrderEntity::class,
        AlertEntity::class,
        SyncQueueEntity::class
    ],
    version = 2,
    exportSchema = false
)
@TypeConverters(Converters::class)
abstract class HoneyChainDatabase : RoomDatabase() {
    abstract fun dao(): HoneyChainDao

    companion object {
        @Volatile
        private var INSTANCE: HoneyChainDatabase? = null

        fun getInstance(context: Context): HoneyChainDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    HoneyChainDatabase::class.java,
                    "honey_chain_database.db"
                ).fallbackToDestructiveMigration().build()
                INSTANCE = instance
                instance
            }
        }
    }
}
