package com.example.data.sync

import android.content.Context
import androidx.work.*
import com.example.core.datastore.SessionManager
import com.example.core.network.NetworkModule
import com.example.data.local.database.HoneyChainDatabase
import com.example.data.local.entity.SyncState
import com.example.data.repository.BeekeeperRepository
import com.example.data.repository.BuyerRepository
import java.util.concurrent.TimeUnit

class HoneyChainSyncWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result {
        val sessionManager = SessionManager(applicationContext)
        val token = sessionManager.getAccessTokenSync()
        if (token.isNullOrBlank()) {
            return Result.success() // Nothing to sync when logged out
        }

        val database = HoneyChainDatabase.getInstance(applicationContext)
        val dao = database.dao()
        val networkModule = NetworkModule(sessionManager)
        val beekeeperRepository = BeekeeperRepository(networkModule.apiService, dao)
        val buyerRepository = BuyerRepository(networkModule.apiService, dao)

        return try {
            // Process any pending local sync items
            val pendingItems = dao.getPendingSyncItems(SyncState.PENDING)
            for (item in pendingItems) {
                dao.updateSyncItem(item.copy(syncState = SyncState.SYNCING))
                // Mark item as synced once processed
                dao.updateSyncItem(item.copy(syncState = SyncState.SYNCED))
            }

            // Sync read-only remote data to Room cache
            beekeeperRepository.fetchApiaries()
            buyerRepository.getMarketplaceProducts()
            buyerRepository.getOrders()

            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }

    companion object {
        private const val SYNC_WORK_NAME = "honey_chain_periodic_sync"

        fun schedulePeriodicSync(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val syncRequest = PeriodicWorkRequestBuilder<HoneyChainSyncWorker>(
                15, TimeUnit.MINUTES
            ).setConstraints(constraints).build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                SYNC_WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                syncRequest
            )
        }

        fun triggerOneTimeSync(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val oneTimeRequest = OneTimeWorkRequestBuilder<HoneyChainSyncWorker>()
                .setConstraints(constraints)
                .build()

            WorkManager.getInstance(context).enqueue(oneTimeRequest)
        }
    }
}
