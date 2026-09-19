const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const path = require('path');
const { Pool } = require('pg');
require('dotenv').config();

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: '*' }
});

const PORT = process.env.PORT || 3000;
const API_BASE = '/api/v1';

// PostgreSQL connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

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
  status: "Healthy"
};

const lastBroadcasts = {};
const simIntervalIds = {};

async function getHiveState(hiveId) {
  const result = await pool.query('SELECT * FROM iot_hive_states WHERE hive_id = $1', [hiveId]);
  if (result.rows.length > 0) {
    return result.rows[0];
  }
  return null;
}

async function getAllHives() {
  const result = await pool.query('SELECT * FROM iot_hive_states');
  return result.rows;
}

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
  if (data.sound_level < 30) data.activity_level = "Low";
  else if (data.sound_level <= 70) data.activity_level = "Normal";
  else data.activity_level = "Aggressive";

  if (data.temperature > 40 || data.co2_level > 1000) {
    data.status = "Critical";
  } else if (data.humidity > 80) {
    data.status = "Warning";
  } else {
    data.status = "Healthy";
  }

  data.last_updated = new Date().toISOString();
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

async function updateHiveStateDB(hiveId, state) {
  const query = `
    UPDATE iot_hive_states 
    SET temperature = $1, humidity = $2, weight = $3, sound_level = $4, co2_level = $5, activity_level = $6, status = $7, last_updated = CURRENT_TIMESTAMP
    WHERE hive_id = $8 RETURNING *
  `;
  const values = [
    state.temperature, state.humidity, state.weight, state.sound_level, state.co2_level,
    state.activity_level, state.status, hiveId
  ];
  const result = await pool.query(query, values);
  return result.rows[0];
}

// -----------------------------------
// 10. Real-Time Updates (Throttled Broadcast)
// -----------------------------------
function broadcastUpdate(hiveId, state) {
  const now = Date.now();
  if (!lastBroadcasts[hiveId] || now - lastBroadcasts[hiveId] >= 1000) {
    io.emit('iot-update', { hiveId, data: state });
    lastBroadcasts[hiveId] = now;
  }
}

// Initial connection
io.on('connection', async (socket) => {
  const hives = await getAllHives();
  const data = hives.map(hive => ({
    hiveId: hive.hive_id,
    data: hive
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

app.get(`${API_BASE}/iot-data`, async (req, res) => {
  const hives = await getAllHives();
  const data = hives.map(hive => ({ hiveId: hive.hive_id, data: hive }));
  sendSuccess(res, data);
});

app.get(`${API_BASE}/iot-data/:hiveId`, async (req, res) => {
  const state = await getHiveState(req.params.hiveId);
  if (!state) return sendError(res, "Hive not found");
  sendSuccess(res, { hiveId: req.params.hiveId, data: state });
});

app.post([`${API_BASE}/update-iot/:hiveId`], async (req, res) => {
  const hiveId = req.params.hiveId;
  const err = validateData(req.body);
  if (err) return sendError(res, err);

  const state = await getHiveState(hiveId);
  if (!state) return sendError(res, "Hive not found");

  Object.assign(state, req.body);
  computeDerivedFields(state);
  const updatedState = await updateHiveStateDB(hiveId, state);
  
  console.log(`IoT Updated [${hiveId}]:`, updatedState);
  broadcastUpdate(hiveId, updatedState);
  
  sendSuccess(res, updatedState, "Data updated successfully");
});

app.post([`${API_BASE}/set-scenario/:hiveId`], async (req, res) => {
  const hiveId = req.params.hiveId;
  const { scenario } = req.body;
  if (!scenario || !scenarios[scenario]) return sendError(res, "Invalid scenario");

  const state = await getHiveState(hiveId);
  if (!state) return sendError(res, "Hive not found");

  Object.assign(state, scenarios[scenario]);
  computeDerivedFields(state);
  const updatedState = await updateHiveStateDB(hiveId, state);
  
  console.log(`IoT Updated (Scenario) [${hiveId}]:`, updatedState);
  broadcastUpdate(hiveId, updatedState);
  
  sendSuccess(res, updatedState, `Scenario applied`);
});

app.get(`${API_BASE}/health`, (req, res) => {
  res.json({ status: "ok" });
});

app.post([`${API_BASE}/reset/:hiveId`], async (req, res) => {
  const hiveId = req.params.hiveId;
  const state = await getHiveState(hiveId);
  if (!state) return sendError(res, "Hive not found");

  Object.assign(state, defaultState);
  computeDerivedFields(state);
  const updatedState = await updateHiveStateDB(hiveId, state);

  console.log(`IoT Updated (Reset) [${hiveId}]:`, updatedState);
  broadcastUpdate(hiveId, updatedState);
  
  sendSuccess(res, updatedState, `Reset to default`);
});

// -----------------------------------
// 9. Simulation Engine
// -----------------------------------

async function startSimForHive(hiveId, interval) {
  if (simIntervalIds[hiveId]) return false;

  simIntervalIds[hiveId] = setInterval(async () => {
    const state = await getHiveState(hiveId);
    if (!state) {
      clearInterval(simIntervalIds[hiveId]);
      delete simIntervalIds[hiveId];
      return;
    }

    state.temperature += (Math.random() * 1.0 - 0.5);
    state.humidity += (Math.random() * 4.0 - 2.0);
    state.sound_level += (Math.random() * 10.0 - 5.0);
    state.co2_level += (Math.random() * 100.0 - 50.0);
    state.weight += (Math.random() * 0.2 - 0.1);

    state.temperature = Math.max(0, Math.min(60, state.temperature));
    state.humidity = Math.max(0, Math.min(100, state.humidity));
    state.sound_level = Math.max(0, Math.min(120, state.sound_level));
    state.co2_level = Math.max(300, Math.min(2000, state.co2_level));
    state.weight = Math.max(1, state.weight);

    computeDerivedFields(state);
    const updatedState = await updateHiveStateDB(hiveId, state);
    
    console.log(`IoT Updated (Sim) [${hiveId}]:`, updatedState.status, updatedState.activity_level);
    
    io.emit('iot-update', { hiveId, data: updatedState });
    lastBroadcasts[hiveId] = Date.now();
  }, interval);
  return true;
}

app.post([`${API_BASE}/simulate/:hiveId`], async (req, res) => {
  const hiveId = req.params.hiveId;
  if (simIntervalIds[hiveId]) return sendError(res, "Simulation is already running");

  const state = await getHiveState(hiveId);
  if (!state) return sendError(res, "Hive not found");

  let interval = req.body.interval || 2000;
  if (interval < 1000) interval = 1000;

  startSimForHive(hiveId, interval);
  sendSuccess(res, { running: true, interval, hiveId }, `Simulation started`);
});

app.post([`${API_BASE}/stop-simulation/:hiveId`], (req, res) => {
  const hiveId = req.params.hiveId;
  if (simIntervalIds[hiveId]) {
    clearInterval(simIntervalIds[hiveId]);
    delete simIntervalIds[hiveId];
    sendSuccess(res, null, `Simulation stopped`);
  } else {
    sendError(res, `Simulation not running`);
  }
});

app.post(`${API_BASE}/simulate-all`, async (req, res) => {
  const hives = await getAllHives();
  let interval = req.body.interval || 2000;
  if (interval < 1000) interval = 1000;

  let startedCount = 0;
  for (const hive of hives) {
    const started = await startSimForHive(hive.hive_id, interval);
    if (started) startedCount++;
  }
  
  sendSuccess(res, { running: true, interval, startedCount }, `Simulations started for ${startedCount} hives`);
});

app.post(`${API_BASE}/stop-simulation-all`, async (req, res) => {
  const hives = await getAllHives();
  let stoppedCount = 0;
  
  for (const hive of hives) {
    if (simIntervalIds[hive.hive_id]) {
      clearInterval(simIntervalIds[hive.hive_id]);
      delete simIntervalIds[hive.hive_id];
      stoppedCount++;
    }
  }
  
  sendSuccess(res, { stoppedCount }, `Simulations stopped for ${stoppedCount} hives`);
});

server.listen(PORT, () => {
  console.log(`IoT Mock Server connected to PostgreSQL running on port ${PORT}`);
});
