package com.example

import android.app.Application
import com.example.core.datastore.SessionManager
import com.example.core.network.NetworkModule
import com.example.data.local.database.HoneyChainDatabase
import com.example.data.repository.AuthRepository
import com.example.data.repository.BeekeeperRepository
import com.example.data.repository.BuyerRepository
import com.example.data.repository.TraceabilityRepository
import com.example.data.sync.HoneyChainSyncWorker

class HoneyChainApplication : Application() {

    lateinit var sessionManager: SessionManager
        private set

    lateinit var database: HoneyChainDatabase
        private set

    lateinit var networkModule: NetworkModule
        private set

    lateinit var authRepository: AuthRepository
        private set

    lateinit var beekeeperRepository: BeekeeperRepository
        private set

    lateinit var buyerRepository: BuyerRepository
        private set

    lateinit var traceabilityRepository: TraceabilityRepository
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this

        sessionManager = SessionManager(this)
        database = HoneyChainDatabase.getInstance(this)
        networkModule = NetworkModule(sessionManager)

        val dao = database.dao()
        authRepository = AuthRepository(networkModule.apiService, sessionManager, dao)
        beekeeperRepository = BeekeeperRepository(networkModule.apiService, dao)
        buyerRepository = BuyerRepository(networkModule.apiService, dao)
        traceabilityRepository = TraceabilityRepository(networkModule.apiService)

        // Schedule periodic sync
        try {
            HoneyChainSyncWorker.schedulePeriodicSync(this)
        } catch (_: Exception) {
            // Background workers might be constrained in certain headless environments
        }
    }

    companion object {
        lateinit var instance: HoneyChainApplication
            private set
    }
}
