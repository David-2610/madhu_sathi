package com.example.core.datastore

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.example.BuildConfig
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "honey_chain_session")

class SessionManager(private val context: Context) {

    companion object {
        val KEY_ACCESS_TOKEN = stringPreferencesKey("access_token")
        val KEY_USER_ID = stringPreferencesKey("user_id")
        val KEY_USER_EMAIL = stringPreferencesKey("user_email")
        val KEY_USER_NAME = stringPreferencesKey("user_name")
        val KEY_USER_ROLE = stringPreferencesKey("user_role")
        val KEY_BACKEND_URL = stringPreferencesKey("backend_url")
    }

    @Volatile
    private var cachedBackendUrl: String = BuildConfig.BACKEND_BASE_URL

    @Volatile
    private var cachedAccessToken: String? = null

    init {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                context.dataStore.data.collect { prefs ->
                    cachedBackendUrl = prefs[KEY_BACKEND_URL] ?: BuildConfig.BACKEND_BASE_URL
                    cachedAccessToken = prefs[KEY_ACCESS_TOKEN]
                }
            } catch (_: Exception) {}
        }
    }

    val accessTokenFlow: Flow<String?> = context.dataStore.data.map { prefs ->
        prefs[KEY_ACCESS_TOKEN]
    }

    val userRoleFlow: Flow<String?> = context.dataStore.data.map { prefs ->
        prefs[KEY_USER_ROLE]
    }

    val userNameFlow: Flow<String?> = context.dataStore.data.map { prefs ->
        prefs[KEY_USER_NAME]
    }

    val userEmailFlow: Flow<String?> = context.dataStore.data.map { prefs ->
        prefs[KEY_USER_EMAIL]
    }

    val backendUrlFlow: Flow<String> = context.dataStore.data.map { prefs ->
        prefs[KEY_BACKEND_URL] ?: BuildConfig.BACKEND_BASE_URL
    }

    fun getAccessTokenSync(): String? {
        // Return the in-memory cache populated by the background collect() in init.
        // Using runBlocking here can deadlock against that collect() on Dispatchers.IO.
        return cachedAccessToken
    }

    fun getBackendUrlSync(): String {
        return cachedBackendUrl
    }

    suspend fun saveSession(
        token: String,
        userId: String? = null,
        email: String? = null,
        name: String? = null,
        role: String? = null
    ) {
        context.dataStore.edit { prefs ->
            prefs[KEY_ACCESS_TOKEN] = token
            if (userId != null) prefs[KEY_USER_ID] = userId
            if (email != null) prefs[KEY_USER_EMAIL] = email
            if (name != null) prefs[KEY_USER_NAME] = name
            if (role != null) prefs[KEY_USER_ROLE] = role.uppercase()
        }
    }

    suspend fun updateUserInfo(
        userId: String,
        email: String,
        name: String,
        role: String
    ) {
        context.dataStore.edit { prefs ->
            prefs[KEY_USER_ID] = userId
            prefs[KEY_USER_EMAIL] = email
            prefs[KEY_USER_NAME] = name
            prefs[KEY_USER_ROLE] = role.uppercase()
        }
    }

    suspend fun setBackendUrl(url: String) {
        val trimmed = url.trim()
        val normalized = if (trimmed.endsWith("/")) trimmed else "$trimmed/"
        cachedBackendUrl = normalized
        context.dataStore.edit { prefs ->
            prefs[KEY_BACKEND_URL] = normalized
        }
    }

    suspend fun clearSession() {
        context.dataStore.edit { prefs ->
            prefs.remove(KEY_ACCESS_TOKEN)
            prefs.remove(KEY_USER_ID)
            prefs.remove(KEY_USER_EMAIL)
            prefs.remove(KEY_USER_NAME)
            prefs.remove(KEY_USER_ROLE)
        }
    }
}
