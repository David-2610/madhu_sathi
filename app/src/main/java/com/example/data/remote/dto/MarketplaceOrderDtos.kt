package com.example.data.remote.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class ProductListingDto(
    @Json(name = "product_id") val productId: String = "",
    @Json(name = "is_listed") val isListed: Boolean = true,
    @Json(name = "price") val price: Double = 0.0,
    @Json(name = "currency") val currency: String = "INR",
    @Json(name = "stock_quantity") val stockQuantity: Int = 1
)

@JsonClass(generateAdapter = true)
data class UpdateListingRequest(
    @Json(name = "price") val price: Double,
    @Json(name = "is_listed") val isListed: Boolean,
    @Json(name = "currency") val currency: String = "INR"
)

@JsonClass(generateAdapter = true)
data class CartItemDto(
    @Json(name = "id") val id: String? = null,
    @Json(name = "product_id") val productId: String = "",
    @Json(name = "serial_number") val serialNumber: String? = null,
    @Json(name = "honey_type") val honeyType: String? = null,
    @Json(name = "net_weight_g") val netWeightG: Double? = null,
    @Json(name = "price") val priceStr: String? = null,
    @Json(name = "price_at_addition") val priceAtAddition: Double? = null,
    @Json(name = "currency") val currency: String? = "INR",
    @Json(name = "is_available") val isAvailable: Boolean = true,
    @Json(name = "title") val itemTitle: String? = null,
    @Json(name = "jar_size_grams") val jarSizeGramsLegacy: Int? = null,
    @Json(name = "unit_price") val unitPriceLegacy: Double? = null,
    @Json(name = "quantity") val quantity: Int = 1,
    @Json(name = "subtotal") val subtotalLegacy: Double? = null
) {
    val jarSizeGrams: Int get() = netWeightG?.toInt() ?: jarSizeGramsLegacy ?: 500
    val title: String get() = itemTitle ?: (if (!honeyType.isNullOrBlank()) "$honeyType Honey (${jarSizeGrams}g)" else (serialNumber ?: "Pure Honey Jar"))
    val unitPrice: Double get() = priceStr?.toDoubleOrNull() ?: priceAtAddition ?: unitPriceLegacy ?: 450.0
    val subtotal: Double get() = subtotalLegacy ?: (unitPrice * quantity)
}

@JsonClass(generateAdapter = true)
data class CartDto(
    @Json(name = "id") val id: String? = null,
    @Json(name = "buyer_id") val buyerId: String? = null,
    @Json(name = "items") val items: List<CartItemDto> = emptyList(),
    @Json(name = "subtotal_amount") val subtotalAmountStr: String? = null,
    @Json(name = "total_price") val totalPriceLegacy: Double? = null,
    @Json(name = "total_items") val totalItemsBackend: Int? = null,
    @Json(name = "currency") val currency: String? = "INR"
) {
    val totalPrice: Double get() = subtotalAmountStr?.toDoubleOrNull() ?: totalPriceLegacy ?: items.sumOf { it.subtotal }
    val totalItems: Int get() = totalItemsBackend ?: items.sumOf { it.quantity }
}

@JsonClass(generateAdapter = true)
data class AddToCartRequest(
    @Json(name = "product_id") val productId: Int
)

@JsonClass(generateAdapter = true)
data class ShippingAddressDto(
    @Json(name = "full_name") val fullName: String = "Rural Honey Buyer",
    @Json(name = "phone") val phone: String = "9876543210",
    @Json(name = "address_line1") val addressLine1: String = "42 Kisan Hub Road",
    @Json(name = "address_line2") val addressLine2: String? = "Near Mandi",
    @Json(name = "city") val city: String = "Bharatpur",
    @Json(name = "district") val district: String = "Bharatpur",
    @Json(name = "state") val state: String = "Rajasthan",
    @Json(name = "pincode") val pincode: String = "321602"
)

@JsonClass(generateAdapter = true)
data class CheckoutRequest(
    @Json(name = "shipping_address") val shippingAddress: ShippingAddressDto = ShippingAddressDto()
)

@JsonClass(generateAdapter = true)
data class OrderItemDto(
    @Json(name = "id") val id: String? = null,
    @Json(name = "product_id") val productId: String = "",
    @Json(name = "product_serial") val productSerial: String? = null,
    @Json(name = "honey_type") val honeyType: String? = null,
    @Json(name = "net_weight_g") val netWeightG: Double? = null,
    @Json(name = "unit_price") val unitPriceStr: String? = null,
    @Json(name = "currency") val currency: String? = "INR",
    @Json(name = "batch_code") val batchCode: String? = null,
    @Json(name = "beekeeper_code") val beekeeperCode: String? = null,
    @Json(name = "beekeeper_name") val beekeeperName: String? = null,
    @Json(name = "apiary_name") val apiaryName: String? = null,
    @Json(name = "price") val itemPrice: Double? = null,
    @Json(name = "title") val titleLegacy: String? = null,
    @Json(name = "quantity") val quantity: Int = 1,
    @Json(name = "unit_price_legacy") val unitPriceLegacy: Double? = null,
    @Json(name = "subtotal") val subtotalLegacy: Double? = null
) {
    val title: String get() = titleLegacy ?: (if (!honeyType.isNullOrBlank()) "$honeyType Honey (${netWeightG?.toInt() ?: 500}g)" else (productSerial ?: "Pure Honey Jar"))
    val unitPrice: Double get() = unitPriceStr?.toDoubleOrNull() ?: itemPrice ?: unitPriceLegacy ?: 450.0
    val subtotal: Double get() = subtotalLegacy ?: (unitPrice * quantity)
}

@JsonClass(generateAdapter = true)
data class PaymentSummaryDto(
    @Json(name = "id") val id: String? = null,
    @Json(name = "payment_reference") val paymentReference: String = "",
    @Json(name = "provider") val provider: String = "MOCK",
    @Json(name = "amount") val amountStr: String? = null,
    @Json(name = "currency") val currency: String = "INR",
    @Json(name = "status") val status: String = "CAPTURED",
    @Json(name = "is_mock") val isMock: Boolean = true
) {
    val amount: Double get() = amountStr?.toDoubleOrNull() ?: 0.0
}

@JsonClass(generateAdapter = true)
data class OrderDto(
    @Json(name = "id") val id: String = "",
    @Json(name = "order_number") val orderNumber: String? = null,
    @Json(name = "order_code") val orderCode: String? = null,
    @Json(name = "buyer_id") val buyerId: String? = null,
    @Json(name = "items") val items: List<OrderItemDto> = emptyList(),
    @Json(name = "subtotal_amount") val subtotalAmountStr: String? = null,
    @Json(name = "shipping_amount") val shippingAmountStr: String? = null,
    @Json(name = "total_amount") val totalAmountStr: String? = null,
    @Json(name = "total_amount_legacy") val totalAmountLegacy: Double? = null,
    @Json(name = "currency") val currency: String = "INR",
    @Json(name = "status") val status: String = "PENDING_PAYMENT",
    @Json(name = "payment_status") val paymentStatusField: String? = null,
    @Json(name = "shipping_address") val shippingAddress: ShippingAddressDto? = null,
    @Json(name = "latest_payment") val latestPayment: PaymentSummaryDto? = null,
    @Json(name = "created_at") val createdAt: String? = null
) {
    val totalAmount: Double get() = totalAmountStr?.toDoubleOrNull() ?: totalAmountLegacy ?: 0.0
    val subtotalAmount: Double get() = subtotalAmountStr?.toDoubleOrNull() ?: totalAmount
    val shippingAmount: Double get() = shippingAmountStr?.toDoubleOrNull() ?: 0.0
    val displayOrderCode: String get() = orderNumber ?: orderCode ?: ("ORD-" + id.takeLast(6))
    val paymentStatus: String get() = latestPayment?.status ?: paymentStatusField ?: if (status == "PAID" || status == "COMPLETED") "PAID" else "PENDING"
}

@JsonClass(generateAdapter = true)
data class PaymentDetailDto(
    @Json(name = "order_id") val orderId: String,
    @Json(name = "amount") val amount: Double,
    @Json(name = "payment_method") val paymentMethod: String = "MOCK",
    @Json(name = "status") val status: String = "PAID",
    @Json(name = "transaction_id") val transactionId: String? = null,
    @Json(name = "is_mock") val isMock: Boolean = true
)

@JsonClass(generateAdapter = true)
data class PaymentConfirmRequest(
    @Json(name = "mock_success") val mockSuccess: Boolean = true
)
