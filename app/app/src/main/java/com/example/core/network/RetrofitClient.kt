package com.example.core.network

import com.example.BuildConfig
import com.example.core.datastore.SessionManager
import com.example.data.remote.api.HoneyChainApiService
import com.squareup.moshi.FromJson
import com.squareup.moshi.JsonReader
import com.squareup.moshi.JsonWriter
import com.squareup.moshi.Moshi
import com.squareup.moshi.ToJson
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit

class LenientStringAdapter {
    @FromJson
    fun fromJson(reader: JsonReader): String {
        return when (reader.peek()) {
            JsonReader.Token.STRING -> reader.nextString()
            JsonReader.Token.NUMBER -> reader.nextString()
            JsonReader.Token.BOOLEAN -> reader.nextBoolean().toString()
            JsonReader.Token.NULL -> {
                reader.nextNull<Unit>()
                ""
            }
            else -> {
                reader.skipValue()
                ""
            }
        }
    }

    @ToJson
    fun toJson(writer: JsonWriter, value: String?) {
        writer.value(value)
    }
}

class NetworkModule(
    private val sessionManager: SessionManager,
    private val onUnauthorized: () -> Unit = {}
) {
    val moshi: Moshi = Moshi.Builder()
        .add(LenientStringAdapter())
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
        .addInterceptor(AuthInterceptor(sessionManager, onUnauthorized))
        .addInterceptor(loggingInterceptor)
        .build()

    val apiService: HoneyChainApiService = Retrofit.Builder()
        .baseUrl(BuildConfig.BACKEND_BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(MoshiConverterFactory.create(moshi))
        .build()
        .create(HoneyChainApiService::class.java)

    val webSocketManager = WebSocketManager(
        sessionManager = sessionManager,
        client = okHttpClient,
        moshi = moshi
    )
}
