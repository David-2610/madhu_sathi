const socket = io();
const API_BASE = '/api/v1';

// Elements
const elTemp = document.getElementById('val-temp');
const elHum = document.getElementById('val-hum');
const elWeight = document.getElementById('val-weight');
const elSound = document.getElementById('val-sound');
const elCo2 = document.getElementById('val-co2');
const elTimestamp = document.getElementById('val-timestamp');
const elStatusBadge = document.getElementById('status-badge');
const elActivityBadge = document.getElementById('activity-badge');

const sldTemp = document.getElementById('slider-temp');
const sldHum = document.getElementById('slider-hum');
const sldWeight = document.getElementById('slider-weight');
const sldSound = document.getElementById('slider-sound');
const sldCo2 = document.getElementById('slider-co2');

const sldValTemp = document.getElementById('slide-val-temp');
const sldValHum = document.getElementById('slide-val-hum');
const sldValWeight = document.getElementById('slide-val-weight');
const sldValSound = document.getElementById('slide-val-sound');
const sldValCo2 = document.getElementById('slide-val-co2');

const hiveSelect = document.getElementById('hive-select');
const newHiveInput = document.getElementById('new-hive-id');

let hives = {};
let currentHiveId = "HIVE_001";

// Socket Listener
socket.on('initial-data', (dataArray) => {
  hives = {};
  hiveSelect.innerHTML = '';
  dataArray.forEach(item => {
    hives[item.hiveId] = item.data;
    addHiveToDropdown(item.hiveId);
  });
  
  if (!hives[currentHiveId] && dataArray.length > 0) {
    currentHiveId = dataArray[0].hiveId;
  }
  hiveSelect.value = currentHiveId;
  if (hives[currentHiveId]) {
    updateDashboard(hives[currentHiveId]);
    updateSliders(hives[currentHiveId]);
  }
});

socket.on('iot-update', (payload) => {
  // Support BOTH formats (backward compatibility)
  if (payload.hiveId) {
    // New system format: { hiveId, data }
    hives[payload.hiveId] = payload.data;
    if (!hiveSelect.querySelector(`option[value="${payload.hiveId}"]`)) {
      addHiveToDropdown(payload.hiveId);
    }
    
    if (payload.hiveId === currentHiveId) {
      updateDashboard(payload.data);
      updateSliders(payload.data);
    }
  } else {
    // Old system fallback (assumes single hive or defaults to HIVE_001)
    const data = payload;
    hives["HIVE_001"] = data;
    if (currentHiveId === "HIVE_001") {
      updateDashboard(data);
      updateSliders(data);
    }
  }
});

function addHiveToDropdown(hiveId) {
  if (!hiveSelect.querySelector(`option[value="${hiveId}"]`)) {
    const opt = document.createElement('option');
    opt.value = hiveId;
    opt.textContent = hiveId;
    hiveSelect.appendChild(opt);
  }
}

function selectHive(hiveId) {
  currentHiveId = hiveId;
  if (hives[hiveId]) {
    updateDashboard(hives[hiveId]);
    updateSliders(hives[hiveId]);
  }
}

async function registerHive() {
  const hiveId = newHiveInput.value.trim();
  if (!hiveId) return alert("Please enter a Hive ID");
  
  try {
    const res = await fetch(`${API_BASE}/register-hive`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hiveId })
    });
    const data = await res.json();
    if(data.success) {
      newHiveInput.value = '';
      selectHive(hiveId);
      hiveSelect.value = hiveId;
    } else {
      alert(data.error);
    }
  } catch (e) {
    console.error(e);
  }
}

function updateDashboard(data) {
  elTemp.textContent = data.temperature.toFixed(1);
  elHum.textContent = data.humidity.toFixed(1);
  elWeight.textContent = data.weight.toFixed(1);
  elSound.textContent = data.sound_level.toFixed(1);
  elCo2.textContent = Math.round(data.co2_level);
  
  const d = new Date(data.timestamp);
  elTimestamp.textContent = d.toLocaleTimeString() + " " + d.getMilliseconds() + "ms";

  // Status Badge
  elStatusBadge.textContent = data.status;
  elStatusBadge.className = 'badge ' + data.status;

  // Activity Badge
  elActivityBadge.textContent = data.activity_level;
  elActivityBadge.className = 'badge ' + data.activity_level;
}

function updateSliders(data) {
  sldTemp.value = data.temperature;
  sldHum.value = data.humidity;
  sldWeight.value = data.weight;
  sldSound.value = data.sound_level;
  sldCo2.value = data.co2_level;

  sldValTemp.textContent = data.temperature.toFixed(1);
  sldValHum.textContent = data.humidity.toFixed(1);
  sldValWeight.textContent = data.weight.toFixed(1);
  sldValSound.textContent = data.sound_level.toFixed(1);
  sldValCo2.textContent = Math.round(data.co2_level);
}

// Actions
async function setScenario(scenario) {
  try {
    const res = await fetch(`${API_BASE}/set-scenario/${currentHiveId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario })
    });
    const data = await res.json();
    if(!data.success) alert(data.error);
  } catch (e) {
    console.error(e);
  }
}

async function resetState() {
  try {
    await fetch(`${API_BASE}/reset/${currentHiveId}`, { method: 'POST' });
  } catch (e) {
    console.error(e);
  }
}

async function startSimulation() {
  const interval = parseInt(document.getElementById('sim-interval').value) || 2000;
  try {
    const res = await fetch(`${API_BASE}/simulate/${currentHiveId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ interval })
    });
    const data = await res.json();
    if(!data.success) alert(data.error);
  } catch (e) {
    console.error(e);
  }
}

async function stopSimulation() {
  try {
    const res = await fetch(`${API_BASE}/stop-simulation/${currentHiveId}`, { method: 'POST' });
    const data = await res.json();
    if(!data.success) alert(data.error);
  } catch (e) {
    console.error(e);
  }
}

async function startSimulationAll() {
  const interval = parseInt(document.getElementById('sim-interval').value) || 2000;
  try {
    const res = await fetch(`${API_BASE}/simulate-all`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ interval })
    });
    const data = await res.json();
    if(!data.success) alert(data.error);
  } catch (e) {
    console.error(e);
  }
}

async function stopSimulationAll() {
  try {
    const res = await fetch(`${API_BASE}/stop-simulation-all`, { method: 'POST' });
    const data = await res.json();
    if(!data.success) alert(data.error);
  } catch (e) {
    console.error(e);
  }
}

// Manual adjustment
let updateTimeout;
function updateValue(field, value) {
  // Update slider label immediately
  document.getElementById(`slide-val-${field.split('_')[0]}`).textContent = parseFloat(value).toFixed(1);
  
  // Debounce API calls slightly to avoid flooding
  clearTimeout(updateTimeout);
  updateTimeout = setTimeout(async () => {
    try {
      const payload = {};
      payload[field] = parseFloat(value);
      
      await fetch(`${API_BASE}/update-iot/${currentHiveId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch (e) {
      console.error(e);
    }
  }, 100);
}
