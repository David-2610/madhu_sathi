# Honey Chain (Madhu Sathi) – Android Application

Honey Chain (Madhu Sathi) is a smart beekeeping, honey traceability, and direct-to-consumer marketplace platform designed for rural tech empowerment, pure honey authentication, and transparent supply chain integrity.

## Core Features

- **Role-Based Experience**:
  - **Buyer Experience**: Browse authentic single-origin and raw honey varieties, add to cart, calculate real-time pricing and shipping, place orders, and review past orders.
  - **Beekeeper Portal**: Register and monitor apiaries, individual hives, honey harvesting batches, and real-time IoT sensors (temperature, humidity, acoustic frequency, weight, CO2). Access the AI Beekeeping Assistant for advice on colony health, pest control, and seasonal hive maintenance.
  - **KVIC Admin Shell**: High-level governance view to inspect honey quality benchmarks, review harvest batches, audit blockchain cryptographic hashes, and inspect telemetry alerts.
  - **Public QR Traceability Passport**: Quick QR scanner and digital honey passport revealing complete provenance, floral origin, harvest date, moisture content, beekeeper details, and cryptographic batch proof.

- **Offline-First Architecture**:
  - Powered by Android **Room Database** and **WorkManager** background synchronization.
  - Telemetry caching and offline data storage with automatic synchronization when online.

- **Modern Android Stack**:
  - Kotlin & Jetpack Compose with Material 3 theming.
  - State management via ViewModel and Kotlin Coroutines / StateFlow.
  - Type-safe navigation and reactive UI flows.
  - Retrofit + OkHttp networking with WebSocket support for live IoT sensor feeds.

## Build and Run

- Minimum SDK: 24 (Android 7.0)
- Target SDK: 35 (Android 15)
- JDK: 17+
- Build system: Gradle with Kotlin DSL
