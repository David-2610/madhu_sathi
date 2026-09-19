# Mock IoT Simulation Platform

A complete Node.js, Express, and Socket.IO based Mock IoT Simulation Platform mimicking hive sensor behavior. It supports scenario-based control, realistic data simulation streaming, and provides an embedded real-time dashboard. 

## Features
- **Real-Time Data Streaming:** Uses Socket.IO for live data broadcasting to clients.
- **Scenario Engine:** Built-in scenarios like Healthy, Overheating, High Humidity, etc.
- **Simulation Mode:** Realistic continuous data fluctuations simulating active sensors.
- **Embedded Dashboard:** Interactive Control Panel served on `/control`.
- **CORS Enabled:** Ready for consumption by external applications (e.g. Android apps).
- **Validation & Derived Fields:** Automatic state calculation (Status, Activity) and bounds checking.

## Setup Instructions

1. **Install Dependencies:**
   ```bash
   npm install
   ```

2. **Start the Server:**
   ```bash
   node server.js
   # or with nodemon if installed globally
   nodemon server.js
   ```

3. **Access Control Panel:**
   Open a browser and navigate to: [http://localhost:3000/control](http://localhost:3000/control)

## Server Configuration
- **Port:** The server runs on `3000` by default. Can be overridden using the `PORT` environment variable.
- **Base API Path:** `/api/v1`

## Socket.IO Integration
Connect a client to the base server URL. The server emits an `iot-update` event whenever data changes (throttled to 1s max, except during simulation streaming which pushes updates on interval).

**Event:** `'iot-update'`
**Payload Example:**
```json
{
  "temperature": 34,
  "humidity": 60,
  "weight": 30,
  "sound_level": 50,
  "co2_level": 700,
  "activity_level": "Normal",
  "status": "Healthy",
  "timestamp": "2026-09-19T10:00:00.000Z"
}
```

## API Documentation

All standard responses follow this format:
- **Success:** `{ "success": true, "data": { ... }, "message": "optional" }`
- **Error:** `{ "success": false, "error": "Error message" }`

### `GET /api/v1/iot-data`
Returns the current IoT state.

### `POST /api/v1/update-iot`
Updates partial fields manually.
- **Body:** `{ "temperature": 36.5 }`

### `POST /api/v1/set-scenario`
Applies a predefined scenario.
- **Body:** `{ "scenario": "overheating" }`
- Valid Scenarios: `healthy`, `overheating`, `humidity`, `stress`, `low`.

### `POST /api/v1/simulate`
Starts the auto-simulation engine.
- **Body (optional):** `{ "interval": 2000 }` (default 2000ms)

### `POST /api/v1/stop-simulation`
Stops the auto-simulation engine.

### `POST /api/v1/reset`
Resets the server to the default healthy state.

### `GET /api/v1/health`
Basic health check.
- **Response:** `{ "status": "ok" }`
