package com.example.presentation.buyer

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.core.network.ApiResult
import com.example.data.remote.dto.CartDto
import com.example.data.remote.dto.OrderDto
import com.example.data.remote.dto.ProductDto
import com.example.data.repository.BuyerRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class BuyerUiState(
    val isLoadingProducts: Boolean = false,
    val products: List<ProductDto> = emptyList(),
    val productError: String? = null,

    val isLoadingCart: Boolean = false,
    val cart: CartDto = CartDto(),
    val cartError: String? = null,

    val isLoadingOrders: Boolean = false,
    val orders: List<OrderDto> = emptyList(),
    val ordersError: String? = null,

    val checkoutSuccessOrder: OrderDto? = null,
    val isCheckingOut: Boolean = false,
    val checkoutError: String? = null,

    val actionMessage: String? = null
)

class BuyerViewModel(
    private val buyerRepository: BuyerRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(BuyerUiState())
    val uiState: StateFlow<BuyerUiState> = _uiState.asStateFlow()

    init {
        loadMarketplace()
        loadCart()
        loadOrders()
    }

    fun loadMarketplace() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoadingProducts = true, productError = null)
            when (val res = buyerRepository.getMarketplaceProducts()) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoadingProducts = false,
                        products = res.data
                    )
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoadingProducts = false,
                        productError = res.message
                    )
                }
                else -> {}
            }
        }
    }

    fun loadCart() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoadingCart = true, cartError = null)
            when (val res = buyerRepository.getCart()) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoadingCart = false,
                        cart = res.data
                    )
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoadingCart = false,
                        cartError = res.message
                    )
                }
                else -> {}
            }
        }
    }

    fun addToCart(productId: String, quantity: Int = 1) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoadingCart = true)
            when (val res = buyerRepository.addToCart(productId, quantity)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoadingCart = false,
                        cart = res.data,
                        actionMessage = "Item added to cart!"
                    )
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoadingCart = false,
                        cartError = res.message
                    )
                }
                else -> {}
            }
        }
    }

    fun removeFromCart(productId: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoadingCart = true)
            when (val res = buyerRepository.removeFromCart(productId)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoadingCart = false,
                        cart = res.data
                    )
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoadingCart = false,
                        cartError = res.message
                    )
                }
                else -> {}
            }
        }
    }

    fun checkout(onComplete: (orderId: String) -> Unit) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isCheckingOut = true, checkoutError = null)
            when (val res = buyerRepository.checkout()) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isCheckingOut = false,
                        checkoutSuccessOrder = res.data,
                        cart = CartDto() // Cart cleared on checkout
                    )
                    loadOrders()
                    onComplete(res.data.id)
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isCheckingOut = false,
                        checkoutError = res.message
                    )
                }
                else -> {}
            }
        }
    }

    fun confirmPayment(orderId: String, onPaid: () -> Unit) {
        viewModelScope.launch {
            when (val res = buyerRepository.confirmPayment(orderId, "MOCK_UPI")) {
                is ApiResult.Success -> {
                    loadOrders()
                    onPaid()
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(ordersError = res.message)
                }
                else -> {}
            }
        }
    }

    fun loadOrders() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoadingOrders = true, ordersError = null)
            when (val res = buyerRepository.getOrders()) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoadingOrders = false,
                        orders = res.data
                    )
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoadingOrders = false,
                        ordersError = res.message
                    )
                }
                else -> {}
            }
        }
    }

    fun clearActionMessage() {
        _uiState.value = _uiState.value.copy(actionMessage = null)
    }
}
