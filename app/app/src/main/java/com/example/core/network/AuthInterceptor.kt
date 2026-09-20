package com.example.core.network

import com.example.core.datastore.SessionManager
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response

class AuthInterceptor(
    private val sessionManager: SessionManager,
    private val onUnauthorized: () -> Unit = {}
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()
        val path = originalRequest.url.encodedPath

        // Public routes that do not require Authorization header
        val isPublicRoute = path.contains("auth/login") ||
                path.contains("auth/register") ||
                path.contains("/health") ||
                path.contains("/trace/")

        val token = if (!isPublicRoute) sessionManager.getAccessTokenSync() else null

        val newRequestBuilder = originalRequest.newBuilder()
        if (!token.isNullOrBlank()) {
            newRequestBuilder.header("Authorization", "Bearer $token")
        }
        newRequestBuilder.header("Accept", "application/json")

        val response = chain.proceed(newRequestBuilder.build())

        if (response.code == 401 && !isPublicRoute) {
            runBlocking {
                sessionManager.clearSession()
            }
            onUnauthorized()
        }

        return response
    }
}
