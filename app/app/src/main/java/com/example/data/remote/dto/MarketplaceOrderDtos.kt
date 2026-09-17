package com.example.data.remote.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class ProductListingDto(
    @Json(name = "product_id") val productId: String,
    @Json(name = "is_listed") val isListed: Boolean,
    @Json(name = "price") val price: Double,
    @Json(name = "stock_quantity") val stockQuantity: Int = 1
)

@JsonClass(generateAdapter = true)
data class UpdateListingRequest(
    @Json(name = "is_listed") val isListed: Boolean,
    @Json(name = "price") val price: Double? = null,
    @Json(name = "stock_quantity") val stockQuantity: Int? = null
)

@JsonClass(generateAdapter = true)
data class CartItemDto(
    @Json(name = "product_id") val productId: String,
    @Json(name = "title") val title: String,
    @Json(name = "jar_size_grams") val jarSizeGrams: Int = 500,
    @Json(name = "unit_price") val unitPrice: Double,
    @Json(name = "quantity") val quantity: Int,
    @Json(name = "subtotal") val subtotal: Double
)

@JsonClass(generateAdapter = true)
data class CartDto(
    @Json(name = "items") val items: List<CartItemDto> = emptyList(),
    @Json(name = "total_price") val totalPrice: Double = 0.0,
    @Json(name = "total_items") val totalItems: Int = 0
)

@JsonClass(generateAdapter = true)
data class AddToCartRequest(
    @Json(name = "product_id") val productId: String,
    @Json(name = "quantity") val quantity: Int = 1
)

@JsonClass(generateAdapter = true)
data class OrderItemDto(
    @Json(name = "product_id") val productId: String,
    @Json(name = "title") val title: String,
    @Json(name = "quantity") val quantity: Int,
    @Json(name = "unit_price") val unitPrice: Double,
    @Json(name = "subtotal") val subtotal: Double
)

@JsonClass(generateAdapter = true)
data class OrderDto(
    @Json(name = "id") val id: String,
    @Json(name = "buyer_id") val buyerId: String? = null,
    @Json(name = "items") val items: List<OrderItemDto> = emptyList(),
    @Json(name = "total_amount") val totalAmount: Double = 0.0,
    @Json(name = "status") val status: String = "PENDING",
    @Json(name = "payment_status") val paymentStatus: String = "PENDING",
    @Json(name = "created_at") val createdAt: String? = null
)

@JsonClass(generateAdapter = true)
data class PaymentDetailDto(
    @Json(name = "order_id") val orderId: String,
    @Json(name = "amount") val amount: Double,
    @Json(name = "payment_method") val paymentMethod: String = "MOCK",
    @Json(name = "status") val status: String = "PENDING",
    @Json(name = "transaction_id") val transactionId: String? = null,
    @Json(name = "is_mock") val isMock: Boolean = true
)

@JsonClass(generateAdapter = true)
data class PaymentConfirmRequest(
    @Json(name = "payment_method") val paymentMethod: String = "MOCK",
    @Json(name = "transaction_id") val transactionId: String? = null
)
