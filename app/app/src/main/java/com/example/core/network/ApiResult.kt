package com.example.core.network

sealed class ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>()
    data class Error(
        val code: Int? = null,
        val message: String,
        val fieldErrors: Map<String, String> = emptyMap()
    ) : ApiResult<Nothing>()
    data object Loading : ApiResult<Nothing>()

    val isSuccess: Boolean get() = this is Success
    val isError: Boolean get() = this is Error

    fun getOrNull(): T? = (this as? Success)?.data
}
