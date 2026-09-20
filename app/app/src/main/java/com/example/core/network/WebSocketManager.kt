package com.example.core.network

import com.example.BuildConfig
import com.example.core.datastore.SessionManager
import com.example.data.remote.dto.WebSocketEvent
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import okhttp3.*
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import kotlin.math.pow

enum class WebSocketState {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    RECONNECTING
}

class WebSocketManager(
    private val sessionManager: SessionManager,
    private val client: OkHttpClient,
    private val moshi: Moshi
) : WebSocketListener() {

    private val _connectionState = MutableStateFlow(WebSocketState.DISCONNECTED)
    val connectionState: StateFlow<WebSocketState> = _connectionState.asStateFlow()

    private val _events = MutableSharedFlow<WebSocketEvent>(replay = 1, extraBufferCapacity = 64)
    val events: SharedFlow<WebSocketEvent> = _events.asSharedFlow()

    private var webSocket: WebSocket? = null
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    
    private var isIntentionalClose = false
    private var reconnectAttempt = 0
    private var reconnectJob: Job? = null

    fun connect() {
        if (_connectionState.value == WebSocketState.CONNECTED || _connectionState.value == WebSocketState.CONNECTING) return
        
        isIntentionalClose = false
        _connectionState.value = if (reconnectAttempt > 0) WebSocketState.RECONNECTING else WebSocketState.CONNECTING

        scope.launch {
            val token = sessionManager.accessTokenFlow.first() ?: return@launch
            val wsUrl = BuildConfig.BACKEND_BASE_URL.replace("http", "ws") + "kvic/ws?token=$token"
            
            val request = Request.Builder()
                .url(wsUrl)
                .build()

            webSocket = client.newWebSocket(request, this@WebSocketManager)
        }
    }

    fun disconnect() {
        isIntentionalClose = true
        reconnectJob?.cancel()
        webSocket?.close(1000, "User logout/disconnect")
        webSocket = null
        _connectionState.value = WebSocketState.DISCONNECTED
    }

    override fun onOpen(webSocket: WebSocket, response: Response) {
        super.onOpen(webSocket, response)
        reconnectAttempt = 0
        _connectionState.value = WebSocketState.CONNECTED
    }

    override fun onMessage(webSocket: WebSocket, text: String) {
        super.onMessage(webSocket, text)
        scope.launch {
            try {
                // Peek at the event type first using org.json
                val jsonObject = JSONObject(text)
                val eventType = jsonObject.optString("type", jsonObject.optString("event", ""))
                
                // We'll extract the data payload. Sometimes the payload is flattened, sometimes nested in "data"
                val payloadJson = if (jsonObject.has("data")) jsonObject.getJSONObject("data").toString() else text
                
                val event: WebSocketEvent? = when (eventType) {
                    "iot-update" -> moshi.adapter(WebSocketEvent.IotUpdate::class.java).fromJson(payloadJson)
                    "alert" -> moshi.adapter(WebSocketEvent.Alert::class.java).fromJson(payloadJson)
                    "ai-analysis" -> moshi.adapter(WebSocketEvent.AiAnalysis::class.java).fromJson(payloadJson)
                    "initial-data" -> moshi.adapter(WebSocketEvent.InitialData::class.java).fromJson(payloadJson)
                    else -> null
                }
                
                event?.let { _events.emit(it) }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
        super.onClosed(webSocket, code, reason)
        this.webSocket = null
        if (!isIntentionalClose) {
            scheduleReconnect()
        } else {
            _connectionState.value = WebSocketState.DISCONNECTED
        }
    }

    override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
        super.onFailure(webSocket, t, response)
        this.webSocket = null
        if (!isIntentionalClose) {
            scheduleReconnect()
        }
    }

    private fun scheduleReconnect() {
        if (isIntentionalClose) return
        
        _connectionState.value = WebSocketState.RECONNECTING
        reconnectJob?.cancel()
        reconnectJob = scope.launch {
            // Exponential backoff: 2s, 4s, 8s, up to 30s max
            val backoffSeconds = (2.0.pow(reconnectAttempt.coerceAtMost(4))).toLong()
            delay(backoffSeconds * 1000)
            reconnectAttempt++
            connect()
        }
    }
}
