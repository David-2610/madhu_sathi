package com.example.core.navigation

enum class UserRole(val value: String) {
    BUYER("BUYER"),
    BEEKEEPER("BEEKEEPER"),
    KVIC_ADMIN("KVIC_ADMIN");

    companion object {
        fun fromString(role: String?): UserRole {
            return when (role?.uppercase()) {
                "BUYER" -> BUYER
                "BEEKEEPER" -> BEEKEEPER
                "KVIC_ADMIN", "ADMIN" -> KVIC_ADMIN
                else -> BUYER
            }
        }
    }
}

typealias Role = UserRole
