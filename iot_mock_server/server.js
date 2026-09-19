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
const DEFAULT_HIVE = "HIVE_001";

const defaultState = {
  temperature: 34,
  humidity: 60,
  weight: 30,
  sound_level: 50,
  co2_level: 700,
  activity_level: "Normal",
  status: "Healthy"
};

const iotHives = {};
const lastBroadcasts = {};
const simIntervalIds = {};

function getHiveState(hiveId) {
  if (!iotHives[hiveId]) {
    iotHives[hiveId] = { ...defaultState, timestamp: new Date().toISOString() };
  }
  return iotHives[hiveId];
}

// Initialize default hive
getHiveState(DEFAULT_HIVE);

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
function broadcastUpdate(hiveId) {
  const now = Date.now();
  if (!lastBroadcasts[hiveId] || now - lastBroadcasts[hiveId] >= 1000) {
    io.emit('iot-update', { hiveId, data: iotHives[hiveId] });
    lastBroadcasts[hiveId] = now;
  }
}

// Initial connection
io.on('connection', (socket) => {
  // Emit all current hives
  const data = Object.keys(iotHives).map(hiveId => ({
    hiveId,
    data: iotHives[hiveId]
  }));
  socket.emit('initial-data', data);
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
  const data = Object.keys(iotHives).map(hiveId => ({
    hiveId,
    data: iotHives[hiveId]
  }));
  sendSuccess(res, data);
});

// GET /iot-data/:hiveId
app.get(`${API_BASE}/iot-data/:hiveId`, (req, res) => {
  const hiveId = req.params.hiveId;
  const state = getHiveState(hiveId);
  sendSuccess(res, { hiveId, data: state });
});

// POST /register-hive
app.post(`${API_BASE}/register-hive`, (req, res) => {
  const { hiveId } = req.body;
  if (!hiveId) return sendError(res, "Missing hiveId");
  
  const isNew = !iotHives[hiveId];
  const state = getHiveState(hiveId);
  
  if (isNew) {
    console.log(`New hive registered: ${hiveId}`);
    broadcastUpdate(hiveId);
  }
  
  sendSuccess(res, { hiveId, data: state }, `Hive ${hiveId} ready`);
});

// POST /update-iot
app.post([`${API_BASE}/update-iot`, `${API_BASE}/update-iot/:hiveId`], (req, res) => {
  const hiveId = req.params.hiveId || DEFAULT_HIVE;
  const err = validateData(req.body);
  if (err) return sendError(res, err);

  const state = getHiveState(hiveId);
  Object.assign(state, req.body);
  computeDerivedFields(state);
  
  console.log(`IoT Updated [${hiveId}]:`, state);
  broadcastUpdate(hiveId);
  
  sendSuccess(res, state, "Data updated successfully");
});

// POST /set-scenario
app.post([`${API_BASE}/set-scenario`, `${API_BASE}/set-scenario/:hiveId`], (req, res) => {
  const hiveId = req.params.hiveId || DEFAULT_HIVE;
  const { scenario } = req.body;
  if (!scenario || !scenarios[scenario]) {
    return sendError(res, "Invalid or missing scenario");
  }

  const state = getHiveState(hiveId);
  Object.assign(state, scenarios[scenario]);
  computeDerivedFields(state);
  
  console.log(`IoT Updated (Scenario) [${hiveId}]:`, state);
  broadcastUpdate(hiveId);
  
  sendSuccess(res, state, `Scenario '${scenario}' applied to ${hiveId}`);
});

// GET /health
app.get(`${API_BASE}/health`, (req, res) => {
  res.json({ status: "ok" });
});

// POST /reset
app.post([`${API_BASE}/reset`, `${API_BASE}/reset/:hiveId`], (req, res) => {
  const hiveId = req.params.hiveId || DEFAULT_HIVE;
  iotHives[hiveId] = { ...defaultState, timestamp: new Date().toISOString() };
  
  console.log(`IoT Updated (Reset) [${hiveId}]:`, iotHives[hiveId]);
  broadcastUpdate(hiveId);
  
  sendSuccess(res, iotHives[hiveId], `Reset to default state for ${hiveId}`);
});

// -----------------------------------
// 9. Simulation Engine
// -----------------------------------

function startSimForHive(hiveId, interval) {
  if (simIntervalIds[hiveId]) return false;

  simIntervalIds[hiveId] = setInterval(() => {
    const state = getHiveState(hiveId);
    // realistic small fluctuations
    state.temperature += (Math.random() * 1.0 - 0.5); // ±0.5
    state.humidity += (Math.random() * 4.0 - 2.0); // ±2
    state.sound_level += (Math.random() * 10.0 - 5.0); // ±5
    state.co2_level += (Math.random() * 100.0 - 50.0); // ±50
    state.weight += (Math.random() * 0.2 - 0.1); // slow change

    // keep within valid bounds
    state.temperature = Math.max(0, Math.min(60, state.temperature));
    state.humidity = Math.max(0, Math.min(100, state.humidity));
    state.sound_level = Math.max(0, Math.min(120, state.sound_level));
    state.co2_level = Math.max(300, Math.min(2000, state.co2_level));
    state.weight = Math.max(1, state.weight);

    computeDerivedFields(state);
    
    console.log(`IoT Updated (Sim) [${hiveId}]:`, state.status, state.activity_level);
    
    io.emit('iot-update', { hiveId, data: state });
    lastBroadcasts[hiveId] = Date.now();
  }, interval);
  return true;
}

app.post([`${API_BASE}/simulate`, `${API_BASE}/simulate/:hiveId`], (req, res) => {
  const hiveId = req.params.hiveId || DEFAULT_HIVE;
  if (simIntervalIds[hiveId]) {
    return sendError(res, `Simulation is already running for ${hiveId}`);
  }

  let interval = req.body.interval || 2000;
  if (interval < 1000) interval = 1000;

  startSimForHive(hiveId, interval);
  sendSuccess(res, { running: true, interval, hiveId }, `Simulation started for ${hiveId}`);
});

app.post([`${API_BASE}/stop-simulation`, `${API_BASE}/stop-simulation/:hiveId`], (req, res) => {
  const hiveId = req.params.hiveId || DEFAULT_HIVE;
  if (simIntervalIds[hiveId]) {
    clearInterval(simIntervalIds[hiveId]);
    delete simIntervalIds[hiveId];
    sendSuccess(res, null, `Simulation stopped for ${hiveId}`);
  } else {
    sendError(res, `Simulation is not running for ${hiveId}`);
  }
});

app.post(`${API_BASE}/simulate-all`, (req, res) => {
  let interval = req.body.interval || 2000;
  if (interval < 1000) interval = 1000;
  
  let started = 0;
  for (const hiveId of Object.keys(iotHives)) {
    if (startSimForHive(hiveId, interval)) started++;
  }
  sendSuccess(res, { running: true, interval, started }, `Started simulation for ${started} hives`);
});

app.post(`${API_BASE}/stop-simulation-all`, (req, res) => {
  let stopped = 0;
  for (const hiveId of Object.keys(simIntervalIds)) {
    clearInterval(simIntervalIds[hiveId]);
    delete simIntervalIds[hiveId];
    stopped++;
  }
  sendSuccess(res, { stopped }, `Stopped simulation for ${stopped} hives`);
});

// Start Server
server.listen(PORT, () => {
  console.log(`IoT Mock Server running on port ${PORT}`);
});
