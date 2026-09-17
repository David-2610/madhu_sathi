package com.example.core.network

import com.example.BuildConfig
import com.example.core.datastore.SessionManager
import com.example.data.remote.api.HoneyChainApiService
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit

class DynamicBaseUrlInterceptor(private val sessionManager: SessionManager) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()
        val customUrl = sessionManager.getBackendUrlSync().toHttpUrlOrNull()
        if (customUrl != null) {
            val newUrl = originalRequest.url.newBuilder()
                .scheme(customUrl.scheme)
                .host(customUrl.host)
                .port(customUrl.port)
                .build()
            val newRequest = originalRequest.newBuilder().url(newUrl).build()
            return chain.proceed(newRequest)
        }
        return chain.proceed(originalRequest)
    }
}

class NetworkModule(
    private val sessionManager: SessionManager,
    private val onUnauthorized: () -> Unit = {}
) {
    val moshi: Moshi = Moshi.Builder()
        .addLast(KotlinJsonAdapterFactory())
        .build()

    // OkHttp logging: Level.BASIC logs request URL and HTTP response status
    // while strictly preventing logging of passwords, JWT tokens, and secrets.
    private val loggingInterceptor = HttpLoggingInterceptor { message ->
        android.util.Log.d("OkHttp", message)
    }.apply {
        level = if (BuildConfig.DEBUG) {
            HttpLoggingInterceptor.Level.BASIC
        } else {
            HttpLoggingInterceptor.Level.NONE
        }
    }

    val okHttpClient: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .addInterceptor(DynamicBaseUrlInterceptor(sessionManager))
        .addInterceptor(AuthInterceptor(sessionManager, onUnauthorized))
        .addInterceptor(loggingInterceptor)
        .build()

    val apiService: HoneyChainApiService = Retrofit.Builder()
        .baseUrl(sessionManager.getBackendUrlSync())
        .client(okHttpClient)
        .addConverterFactory(MoshiConverterFactory.create(moshi))
        .build()
        .create(HoneyChainApiService::class.java)
}
