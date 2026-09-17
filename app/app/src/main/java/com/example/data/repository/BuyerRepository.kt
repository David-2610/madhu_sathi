package com.example.data.repository

import com.example.core.network.ApiResult
import com.example.core.network.NetworkErrorMapper
import com.example.data.local.dao.HoneyChainDao
import com.example.data.local.entity.OrderEntity
import com.example.data.local.entity.ProductEntity
import com.example.data.local.entity.SyncState
import com.example.data.remote.api.HoneyChainApiService
import com.example.data.remote.dto.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext

class BuyerRepository(
    private val apiService: HoneyChainApiService,
    private val dao: HoneyChainDao
) {

    val cachedOrders: Flow<List<OrderEntity>> = dao.getAllOrders()

    suspend fun getMarketplaceProducts(skip: Int = 0, limit: Int = 50): ApiResult<List<ProductDto>> = withContext(Dispatchers.IO) {
        try {
            val list = apiService.getMarketplaceProducts(skip, limit)
            val entities = list.map {
                ProductEntity(
                    id = it.id,
                    batchId = it.batchId,
                    title = it.title,
                    description = it.description,
                    jarSizeGrams = it.jarSizeGrams,
                    price = it.price,
                    traceToken = it.traceToken,
                    status = it.status,
                    qrCodeUrl = it.qrCodeUrl,
                    isListed = it.isListed,
                    syncState = SyncState.SYNCED
                )
            }
            dao.insertProducts(entities)
            ApiResult.Success(list)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun getProductDetails(productId: String): ApiResult<ProductDto> = withContext(Dispatchers.IO) {
        try {
            val product = apiService.getMarketplaceProductDetails(productId)
            ApiResult.Success(product)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun getCart(): ApiResult<CartDto> = withContext(Dispatchers.IO) {
        try {
            val cart = apiService.getCart()
            ApiResult.Success(cart)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun addToCart(productId: String, quantity: Int = 1): ApiResult<CartDto> = withContext(Dispatchers.IO) {
        try {
            val cart = apiService.addToCart(AddToCartRequest(productId, quantity))
            ApiResult.Success(cart)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun removeFromCart(productId: String): ApiResult<CartDto> = withContext(Dispatchers.IO) {
        try {
            val cart = apiService.removeFromCart(productId)
            ApiResult.Success(cart)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun checkout(): ApiResult<OrderDto> = withContext(Dispatchers.IO) {
        try {
            val order = apiService.checkout()
            dao.insertOrders(
                listOf(
                    OrderEntity(
                        id = order.id,
                        buyerId = order.buyerId,
                        totalAmount = order.totalAmount,
                        status = order.status,
                        paymentStatus = order.paymentStatus,
                        createdAt = order.createdAt,
                        itemsSummary = "${order.items.size} item(s)"
                    )
                )
            )
            ApiResult.Success(order)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun getOrders(): ApiResult<List<OrderDto>> = withContext(Dispatchers.IO) {
        try {
            val orders = apiService.getBuyerOrders()
            val entities = orders.map {
                OrderEntity(
                    id = it.id,
                    buyerId = it.buyerId,
                    totalAmount = it.totalAmount,
                    status = it.status,
                    paymentStatus = it.paymentStatus,
                    createdAt = it.createdAt,
                    itemsSummary = "${it.items.size} item(s)"
                )
            }
            dao.insertOrders(entities)
            ApiResult.Success(orders)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun getOrderDetails(orderId: String): ApiResult<OrderDto> = withContext(Dispatchers.IO) {
        try {
            val order = apiService.getOrderDetails(orderId)
            ApiResult.Success(order)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun getOrderPayment(orderId: String): ApiResult<PaymentDetailDto> = withContext(Dispatchers.IO) {
        try {
            val payment = apiService.getOrderPayment(orderId)
            ApiResult.Success(payment)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }

    suspend fun confirmPayment(orderId: String, paymentMethod: String = "MOCK"): ApiResult<OrderDto> = withContext(Dispatchers.IO) {
        try {
            val order = apiService.confirmPayment(orderId, PaymentConfirmRequest(paymentMethod = paymentMethod))
            ApiResult.Success(order)
        } catch (e: Exception) {
            NetworkErrorMapper.map(e)
        }
    }
}
