package com.example.data.remote.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class RegisterRequest(
    @Json(name = "email") val email: String,
    @Json(name = "password") val password: String,
    @Json(name = "full_name") val fullName: String,
    @Json(name = "role") val role: String, // BUYER or BEEKEEPER
    @Json(name = "phone") val phoneNumber: String
)

@JsonClass(generateAdapter = true)
data class LoginRequest(
    @Json(name = "email") val email: String,
    @Json(name = "password") val password: String
)

@JsonClass(generateAdapter = true)
data class TokenResponse(
    @Json(name = "access_token") val accessToken: String,
    @Json(name = "token_type") val tokenType: String = "bearer"
)

@JsonClass(generateAdapter = true)
data class UserDto(
    @Json(name = "id") val id: String,
    @Json(name = "email") val email: String,
    @Json(name = "full_name") val fullName: String,
    @Json(name = "role") val role: String,
    @Json(name = "phone") val phoneNumber: String,
    @Json(name = "created_at") val createdAt: String? = null
)
