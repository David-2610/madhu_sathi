const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: '*' }
});

const PORT = process.env.PORT || 3000;
const API_BASE = '/api/v1';

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Serve control panel
app.get('/control', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// -----------------------------------
// 3. IoT Data Model (Initial State)
// -----------------------------------
const defaultState = {
  temperature: 34,
  humidity: 60,
  weight: 30,
  sound_level: 50,
  co2_level: 700,
  activity_level: "Normal",
  status: "Healthy",
  timestamp: new Date().toISOString()
};

let iotState = { ...defaultState };

// -----------------------------------
// 5. Scenario Engine
// -----------------------------------
const scenarios = {
  healthy: { temperature: 34, humidity: 60, weight: 30, sound_level: 50, co2_level: 700 },
  overheating: { temperature: 42, humidity: 55, weight: 28, sound_level: 75, co2_level: 900 },
  humidity: { temperature: 30, humidity: 88, weight: 27, sound_level: 40, co2_level: 1100 },
  stress: { temperature: 38, humidity: 70, weight: 26, sound_level: 85, co2_level: 1200 },
  low: { temperature: 32, humidity: 65, weight: 24, sound_level: 20, co2_level: 800 }
};

// -----------------------------------
// 4. Derived Logic
// -----------------------------------
function computeDerivedFields(data) {
  // activity_level
  if (data.sound_level < 30) data.activity_level = "Low";
  else if (data.sound_level <= 70) data.activity_level = "Normal";
  else data.activity_level = "Aggressive";

  // status
  if (data.temperature > 40 || data.co2_level > 1000) {
    data.status = "Critical";
  } else if (data.humidity > 80) {
    data.status = "Warning";
  } else {
    data.status = "Healthy";
  }

  data.timestamp = new Date().toISOString();
  return data;
}

// -----------------------------------
// 6. Validation Layer
// -----------------------------------
function validateData(data) {
  if (data.temperature !== undefined && (data.temperature < 0 || data.temperature > 60)) return "Invalid temperature (0-60)";
  if (data.humidity !== undefined && (data.humidity < 0 || data.humidity > 100)) return "Invalid humidity (0-100)";
  if (data.sound_level !== undefined && (data.sound_level < 0 || data.sound_level > 120)) return "Invalid sound_level (0-120)";
  if (data.co2_level !== undefined && (data.co2_level < 300 || data.co2_level > 2000)) return "Invalid co2_level (300-2000)";
  if (data.weight !== undefined && data.weight <= 0) return "Invalid weight (>0)";
  return null;
}

// -----------------------------------
// 10. Real-Time Updates (Throttled Broadcast)
// -----------------------------------
let lastBroadcast = 0;
function broadcastUpdate() {
  const now = Date.now();
  if (now - lastBroadcast >= 1000) {
    io.emit('iot-update', iotState);
    lastBroadcast = now;
  }
}

// Initial connection
io.on('connection', (socket) => {
  socket.emit('iot-update', iotState);
});

// Helper for responses
function sendSuccess(res, data, message) {
  res.json({ success: true, data, message });
}
function sendError(res, error) {
  res.status(400).json({ success: false, error });
}

// -----------------------------------
// 8. API Endpoints
// -----------------------------------

// GET /iot-data
app.get(`${API_BASE}/iot-data`, (req, res) => {
  sendSuccess(res, iotState);
});

// POST /update-iot
app.post(`${API_BASE}/update-iot`, (req, res) => {
  const err = validateData(req.body);
  if (err) return sendError(res, err);

  Object.assign(iotState, req.body);
  computeDerivedFields(iotState);
  
  console.log("IoT Updated:", iotState);
  broadcastUpdate();
  
  sendSuccess(res, iotState, "Data updated successfully");
});

// POST /set-scenario
app.post(`${API_BASE}/set-scenario`, (req, res) => {
  const { scenario } = req.body;
  if (!scenario || !scenarios[scenario]) {
    return sendError(res, "Invalid or missing scenario");
  }

  Object.assign(iotState, scenarios[scenario]);
  computeDerivedFields(iotState);
  
  console.log("IoT Updated (Scenario):", iotState);
  broadcastUpdate();
  
  sendSuccess(res, iotState, `Scenario '${scenario}' applied`);
});

// GET /health
app.get(`${API_BASE}/health`, (req, res) => {
  res.json({ status: "ok" });
});

// POST /reset
app.post(`${API_BASE}/reset`, (req, res) => {
  iotState = { ...defaultState };
  iotState.timestamp = new Date().toISOString();
  
  console.log("IoT Updated (Reset):", iotState);
  broadcastUpdate();
  
  sendSuccess(res, iotState, "Reset to default state");
});

// -----------------------------------
// 9. Simulation Engine
// -----------------------------------
let simIntervalId = null;

app.post(`${API_BASE}/simulate`, (req, res) => {
  if (simIntervalId) {
    return sendError(res, "Simulation is already running");
  }

  let interval = req.body.interval || 2000;
  if (interval < 1000) interval = 1000;

  simIntervalId = setInterval(() => {
    // realistic small fluctuations
    iotState.temperature += (Math.random() * 1.0 - 0.5); // ±0.5
    iotState.humidity += (Math.random() * 4.0 - 2.0); // ±2
    iotState.sound_level += (Math.random() * 10.0 - 5.0); // ±5
    iotState.co2_level += (Math.random() * 100.0 - 50.0); // ±50
    iotState.weight += (Math.random() * 0.2 - 0.1); // slow change

    // keep within valid bounds
    iotState.temperature = Math.max(0, Math.min(60, iotState.temperature));
    iotState.humidity = Math.max(0, Math.min(100, iotState.humidity));
    iotState.sound_level = Math.max(0, Math.min(120, iotState.sound_level));
    iotState.co2_level = Math.max(300, Math.min(2000, iotState.co2_level));
    iotState.weight = Math.max(1, iotState.weight);

    computeDerivedFields(iotState);
    
    // Explicitly broadcast immediately without throttle limits for simulation, 
    // but the broadcastUpdate helper respects the 1s throttle.
    // If the interval is >= 1000, the throttle won't suppress it.
    console.log("IoT Updated (Simulation tick):", iotState.status, iotState.activity_level);
    
    // Bypass throttle for simulation since it's interval-based, 
    // or just let broadcastUpdate handle it. Let's just emit directly 
    // to ensure simulation is smooth if interval > 1000.
    io.emit('iot-update', iotState);
    lastBroadcast = Date.now();
    
  }, interval);

  sendSuccess(res, { running: true, interval }, "Simulation started");
});

app.post(`${API_BASE}/stop-simulation`, (req, res) => {
  if (simIntervalId) {
    clearInterval(simIntervalId);
    simIntervalId = null;
    sendSuccess(res, null, "Simulation stopped");
  } else {
    sendError(res, "Simulation is not running");
  }
});

// Start Server
server.listen(PORT, () => {
  console.log(`IoT Mock Server running on port ${PORT}`);
});
