package com.example.data.remote.api

import com.example.data.remote.dto.*
import retrofit2.Response
import retrofit2.http.*

interface HoneyChainApiService {

    // ------------------------------------------
    // HEALTH
    // ------------------------------------------

    // ------------------------------------------
    // AUTHENTICATION
    // ------------------------------------------
    @POST("auth/register")
    suspend fun register(@Body request: RegisterRequest): UserDto

    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): TokenResponse

    @GET("auth/me")
    suspend fun getMe(): UserDto

    // ------------------------------------------
    // BEEKEEPER PROFILE
    // ------------------------------------------
    @POST("beekeeper/profile")
    suspend fun createProfile(@Body profile: BeekeeperProfileDto): BeekeeperProfileDto

    @GET("beekeeper/profile")
    suspend fun getProfile(): BeekeeperProfileDto

    @PUT("beekeeper/profile")
    suspend fun updateProfile(@Body profile: BeekeeperProfileDto): BeekeeperProfileDto

    // ------------------------------------------
    // APIARIES
    // ------------------------------------------
    @POST("beekeeper/apiaries")
    suspend fun createApiary(@Body request: CreateApiaryRequest): ApiaryDto

    @GET("beekeeper/apiaries")
    suspend fun getApiaries(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 50
    ): List<ApiaryDto>

    @GET("beekeeper/apiaries/{apiary_id}")
    suspend fun getApiary(@Path("apiary_id") apiaryId: String): ApiaryDto

    @PUT("beekeeper/apiaries/{apiary_id}")
    suspend fun updateApiary(
        @Path("apiary_id") apiaryId: String,
        @Body request: CreateApiaryRequest
    ): ApiaryDto

    @DELETE("beekeeper/apiaries/{apiary_id}")
    suspend fun deleteApiary(@Path("apiary_id") apiaryId: String): Response<Unit>

    // ------------------------------------------
    // HIVES
    // ------------------------------------------
    @POST("beekeeper/apiaries/{apiary_id}/hives")
    suspend fun createHive(
        @Path("apiary_id") apiaryId: String,
        @Body request: CreateHiveRequest
    ): HiveDto

    @GET("beekeeper/apiaries/{apiary_id}/hives")
    suspend fun getHivesForApiary(@Path("apiary_id") apiaryId: String): List<HiveDto>

    @GET("beekeeper/hives/{hive_id}")
    suspend fun getHive(@Path("hive_id") hiveId: String): HiveDto

    @PUT("beekeeper/hives/{hive_id}")
    suspend fun updateHive(
        @Path("hive_id") hiveId: String,
        @Body request: CreateHiveRequest
    ): HiveDto

    @DELETE("beekeeper/hives/{hive_id}")
    suspend fun deleteHive(@Path("hive_id") hiveId: String): Response<Unit>

    // ------------------------------------------
    // HONEY HARVESTS
    // ------------------------------------------
    @POST("beekeeper/hives/{hive_id}/harvests")
    suspend fun createHarvest(
        @Path("hive_id") hiveId: String,
        @Body request: CreateHarvestRequest
    ): HarvestDto

    @GET("beekeeper/hives/{hive_id}/harvests")
    suspend fun getHarvestsForHive(@Path("hive_id") hiveId: String): List<HarvestDto>

    @GET("beekeeper/harvests/{harvest_id}")
    suspend fun getHarvest(@Path("harvest_id") harvestId: String): HarvestDto

    @PUT("beekeeper/harvests/{harvest_id}")
    suspend fun updateHarvest(
        @Path("harvest_id") harvestId: String,
        @Body request: CreateHarvestRequest
    ): HarvestDto

    // ------------------------------------------
    // HONEY BATCHES
    // ------------------------------------------
    @POST("beekeeper/harvests/{harvest_id}/batches")
    suspend fun createBatch(
        @Path("harvest_id") harvestId: String,
        @Body request: CreateBatchRequest
    ): BatchDto

    @GET("beekeeper/batches")
    suspend fun getBatchesForHarvest(): List<BatchDto>

    @GET("beekeeper/batches/{batch_id}")
    suspend fun getBatch(@Path("batch_id") batchId: String): BatchDto

    @PUT("beekeeper/batches/{batch_id}")
    suspend fun updateBatch(
        @Path("batch_id") batchId: String,
        @Body request: CreateBatchRequest
    ): BatchDto

    // ------------------------------------------
    // PRODUCTS & EVENTS
    // ------------------------------------------
    @POST("beekeeper/batches/{batch_id}/products")
    suspend fun createProduct(
        @Path("batch_id") batchId: String,
        @Body request: CreateProductRequest
    ): ProductDto

    @GET("beekeeper/products")
    suspend fun getAllProducts(): List<ProductDto>

    @GET("beekeeper/batches/{batch_id}/products")
    suspend fun getProductsForBatch(@Path("batch_id") batchId: String): List<ProductDto>

    @GET("beekeeper/products/{product_id}")
    suspend fun getProduct(@Path("product_id") productId: String): ProductDto

    @PUT("beekeeper/products/{product_id}")
    suspend fun updateProduct(
        @Path("product_id") productId: String,
        @Body request: CreateProductRequest
    ): ProductDto

    @POST("beekeeper/products/{product_id}/events")
    suspend fun addProductEvent(
        @Path("product_id") productId: String,
        @Body request: CreateProductEventRequest
    ): ProductEventDto

    @GET("beekeeper/products/{product_id}/qr")
    suspend fun getProductQr(@Path("product_id") productId: String): QrResponseDto

    @PUT("beekeeper/products/{product_id}/status")
    suspend fun updateProductStatus(
        @Path("product_id") productId: String,
        @Body request: UpdateProductStatusRequest
    ): ProductDto

    // ------------------------------------------
    // PUBLIC TRACEABILITY (NO AUTH)
    // ------------------------------------------
    @GET("trace/{trace_token}")
    suspend fun getTraceability(@Path("trace_token") traceToken: String): TraceabilityDetailDto

    @GET("trace/{trace_token}/qr")
    suspend fun getTraceQr(@Path("trace_token") traceToken: String): QrResponseDto

    // ------------------------------------------
    // MARKETPLACE (BUYER / BEEKEEPER LISTINGS)
    // ------------------------------------------
    @GET("marketplace/products")
    suspend fun getMarketplaceProducts(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 50
    ): List<ProductDto>

    @GET("marketplace/products/{product_id}")
    suspend fun getMarketplaceProductDetails(@Path("product_id") productId: String): ProductDto

    @GET("beekeeper/products/{product_id}/listing")
    suspend fun getProductListing(@Path("product_id") productId: String): ProductListingDto

    @PUT("beekeeper/products/{product_id}/listing")
    suspend fun updateProductListing(
        @Path("product_id") productId: String,
        @Body request: UpdateListingRequest
    ): ProductListingDto

    // ------------------------------------------
    // BUYER CART
    // ------------------------------------------
    @GET("buyer/cart")
    suspend fun getCart(): CartDto

    @POST("buyer/cart/items")
    suspend fun addToCart(@Body request: AddToCartRequest): CartDto

    @DELETE("buyer/cart/items/{product_id}")
    suspend fun removeFromCart(@Path("product_id") productId: String): CartDto

    // ------------------------------------------
    // BUYER CHECKOUT & ORDERS
    // ------------------------------------------
    @POST("buyer/checkout")
    suspend fun checkout(@Body request: CheckoutRequest = CheckoutRequest()): OrderDto

    @GET("buyer/orders")
    suspend fun getBuyerOrders(): List<OrderDto>

    @GET("buyer/orders/{order_id}")
    suspend fun getOrderDetails(@Path("order_id") orderId: String): OrderDto

    @GET("buyer/orders/{order_id}/payment")
    suspend fun getOrderPayment(@Path("order_id") orderId: String): PaymentDetailDto

    @POST("buyer/orders/{order_id}/payment/confirm")
    suspend fun confirmPayment(
        @Path("order_id") orderId: String,
        @Body request: PaymentConfirmRequest
    ): OrderDto

    // ------------------------------------------
    // IOT / HIVE HEALTH
    // ------------------------------------------
    @POST("beekeeper/hives/{hive_id}/devices")
    suspend fun registerDevice(
        @Path("hive_id") hiveId: String,
        @Body request: RegisterDeviceRequest
    ): HiveDeviceDto

    @GET("beekeeper/hives/{hive_id}/devices")
    suspend fun getHiveDevices(@Path("hive_id") hiveId: String): List<HiveDeviceDto>

    @POST("beekeeper/hives/{hive_id}/telemetry")
    suspend fun submitTelemetry(
        @Path("hive_id") hiveId: String,
        @Body request: TelemetryRequest
    ): TelemetryResponseDto

    @GET("beekeeper/hives/{hive_id}/alerts")
    suspend fun getHiveAlerts(@Path("hive_id") hiveId: String): List<HiveAlertDto>

    @POST("beekeeper/alerts/{alert_id}/acknowledge")
    suspend fun acknowledgeAlert(@Path("alert_id") alertId: String): HiveAlertDto

    @POST("beekeeper/alerts/{alert_id}/resolve")
    suspend fun resolveAlert(@Path("alert_id") alertId: String): HiveAlertDto

    @GET("beekeeper/hives/{hive_id}/health")
    suspend fun getHiveHealth(@Path("hive_id") hiveId: String): HiveHealthDto

    @POST("beekeeper/hives/{hive_id}/assistant")
    suspend fun askHiveAssistant(
        @Path("hive_id") hiveId: String,
        @Body request: AssistantRequest
    ): AssistantResponseDto

    @POST("beekeeper/hives/{hive_id}/simulator/run")
    suspend fun runSimulator(
        @Path("hive_id") hiveId: String,
        @Body request: SimulatorRunRequest = SimulatorRunRequest()
    ): SimulationResultDto

    // ------------------------------------------
    // KVIC DASHBOARD
    // ------------------------------------------
    @GET("kvic/overview")
    suspend fun getKvicOverview(): KvicOverviewDto

    @GET("kvic/hives")
    suspend fun getKvicHives(): List<KvicHiveDto>

    @GET("kvic/alerts")
    suspend fun getKvicAlerts(): List<KvicAlertDto>
}
