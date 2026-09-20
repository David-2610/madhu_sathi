package com.example.core.network

import org.json.JSONObject
import retrofit2.HttpException
import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

object NetworkErrorMapper {

    fun map(throwable: Throwable): ApiResult.Error {
        return when (throwable) {
            is HttpException -> {
                val code = throwable.code()
                val errorBody = throwable.response()?.errorBody()?.string()
                val (message, fieldErrors) = parseErrorBody(errorBody, code)
                ApiResult.Error(code = code, message = message, fieldErrors = fieldErrors)
            }
            is SocketTimeoutException -> ApiResult.Error(
                code = -1,
                message = "Connection timed out. Please check your backend status and try again."
            )
            is UnknownHostException -> ApiResult.Error(
                code = -2,
                message = "Unable to resolve server address. Check your network or backend base URL."
            )
            is ConnectException -> ApiResult.Error(
                code = -3,
                message = "Connection refused. Please ensure the backend is running at the configured URL."
            )
            is IOException -> ApiResult.Error(
                code = -4,
                message = "Network error: ${throwable.localizedMessage ?: "No internet connection"}"
            )
            else -> ApiResult.Error(
                code = -5,
                message = throwable.localizedMessage ?: "An unexpected error occurred"
            )
        }
    }

    private fun parseErrorBody(body: String?, code: Int): Pair<String, Map<String, String>> {
        if (body.isNullOrBlank()) {
            return when (code) {
                400 -> "Bad request. Please verify your input." to emptyMap()
                401 -> "Session expired or unauthorized. Please log in again." to emptyMap()
                403 -> "You do not have permission for this action." to emptyMap()
                404 -> "Requested item or endpoint was not found." to emptyMap()
                409 -> "Conflict: Action could not be completed due to current state." to emptyMap()
                422 -> "Validation error. Please verify the required fields." to emptyMap()
                500 -> "Server encountered an error. Please try again later." to emptyMap()
                else -> "HTTP error $code" to emptyMap()
            }
        }

        try {
            val json = JSONObject(body)
            val fieldErrors = mutableMapOf<String, String>()

            // FastAPI validation error format: {"detail": [{"loc": ["body", "field"], "msg": "..."}]}
            if (json.has("detail")) {
                val detail = json.get("detail")
                if (detail is org.json.JSONArray) {
                    val messages = mutableListOf<String>()
                    for (i in 0 until detail.length()) {
                        val item = detail.optJSONObject(i)
                        if (item != null) {
                            val msg = item.optString("msg", "Invalid value")
                            val loc = item.optJSONArray("loc")
                            val fieldName = if (loc != null && loc.length() > 0) {
                                loc.optString(loc.length() - 1, "")
                            } else ""
                            if (fieldName.isNotBlank()) {
                                fieldErrors[fieldName] = msg
                            }
                            messages.add(if (fieldName.isNotBlank()) "$fieldName: $msg" else msg)
                        }
                    }
                    val combinedMsg = if (messages.isNotEmpty()) messages.joinToString("; ") else "Validation error"
                    return combinedMsg to fieldErrors
                } else if (detail is String) {
                    return detail to emptyMap()
                }
            }

            if (json.has("message")) {
                return json.getString("message") to emptyMap()
            }
            if (json.has("error")) {
                return json.getString("error") to emptyMap()
            }
        } catch (_: Exception) {
            // Fallback to raw or status message
        }

        val fallback = when (code) {
            400 -> "Bad request"
            401 -> "Unauthorized"
            403 -> "You do not have permission for this action."
            404 -> "Resource not found"
            409 -> "Conflict"
            422 -> "Validation failed"
            500 -> "Internal server error"
            else -> "Error $code: $body"
        }
        return fallback to emptyMap()
    }
}
