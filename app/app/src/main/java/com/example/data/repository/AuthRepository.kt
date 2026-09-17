package com.example.data.repository

import com.example.core.datastore.SessionManager
import com.example.core.network.ApiResult
import com.example.core.network.NetworkErrorMapper
import com.example.data.local.dao.HoneyChainDao
import com.example.data.local.entity.UserProfileEntity
import com.example.data.remote.api.HoneyChainApiService
import com.example.data.remote.dto.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext

class AuthRepository(
    private val apiService: HoneyChainApiService,
    private val sessionManager: SessionManager,
    private val dao: HoneyChainDao
) {

    val currentUserProfile: Flow<UserProfileEntity?> = dao.getUserProfile()
    val userRoleFlow: Flow<String?> = sessionManager.userRoleFlow
    val accessTokenFlow: Flow<String?> = sessionManager.accessTokenFlow
    val backendUrlFlow: Flow<String> = sessionManager.backendUrlFlow

    suspend fun checkHealth(): ApiResult<HealthResponse> = withContext(Dispatchers.IO) {
        val url = "${sessionManager.getBackendUrlSync()}health"
        android.util.Log.d("HoneyChainHealth", "--> GET $url")
        try {
            val response = apiService.checkHealth()
            android.util.Log.d("HoneyChainHealth", "<-- 200 {\"status\":\"${response.status}\"}")
            ApiResult.Success(response)
        } catch (e: Exception) {
            android.util.Log.e("HoneyChainHealth", "<-- HTTP FAILED: ${e.javaClass.simpleName}: ${e.message}")
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun register(
        email: String,
        password: String,
        fullName: String,
        role: String,
        phoneNumber: String? = null
    ): ApiResult<UserDto> = withContext(Dispatchers.IO) {
        val url = "${sessionManager.getBackendUrlSync()}auth/register"
        android.util.Log.d("HoneyChainAuth", "--> POST $url (role=$role)")
        try {
            val request = RegisterRequest(
                email = email.trim(),
                password = password,
                fullName = fullName.trim(),
                role = role.uppercase(),
                phoneNumber = phoneNumber?.trim()?.ifBlank { null }
            )
            val user = apiService.register(request)
            android.util.Log.d("HoneyChainAuth", "<-- 200 Registration successful: id=${user.id}")
            ApiResult.Success(user)
        } catch (e: Exception) {
            android.util.Log.e("HoneyChainAuth", "<-- Registration failed: ${e.javaClass.simpleName}: ${e.message}")
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun login(email: String, password: String): ApiResult<UserDto> = withContext(Dispatchers.IO) {
        try {
            val tokenResponse = apiService.login(LoginRequest(email.trim(), password))
            val token = tokenResponse.accessToken

            // Save token in DataStore
            sessionManager.saveSession(token = token)

            // Immediately fetch current authenticated user profile
            val me = apiService.getMe()

            // Update session and local room cache
            sessionManager.updateUserInfo(
                userId = me.id,
                email = me.email,
                name = me.fullName,
                role = me.role
            )

            dao.insertUserProfile(
                UserProfileEntity(
                    id = me.id,
                    email = me.email,
                    fullName = me.fullName,
                    role = me.role,
                    phoneNumber = me.phoneNumber
                )
            )

            ApiResult.Success(me)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun restoreSession(): ApiResult<UserDto> = withContext(Dispatchers.IO) {
        val token = sessionManager.getAccessTokenSync()
        if (token.isNullOrBlank()) {
            return@withContext ApiResult.Error(code = 401, message = "No active session")
        }

        try {
            val me = apiService.getMe()
            sessionManager.updateUserInfo(
                userId = me.id,
                email = me.email,
                name = me.fullName,
                role = me.role
            )
            dao.insertUserProfile(
                UserProfileEntity(
                    id = me.id,
                    email = me.email,
                    fullName = me.fullName,
                    role = me.role,
                    phoneNumber = me.phoneNumber
                )
            )
            ApiResult.Success(me)
        } catch (e: Exception) {
            val err = NetworkErrorMapper.map(e)
            if (err.code == 401) {
                logout()
            }
            err
        }
    }

    suspend fun logout() = withContext(Dispatchers.IO) {
        sessionManager.clearSession()
        dao.clearUserProfile()
        dao.clearApiaries()
    }

    suspend fun updateBackendUrl(url: String) {
        sessionManager.setBackendUrl(url)
    }
}
