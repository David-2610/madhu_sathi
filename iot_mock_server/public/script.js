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

// Socket Listener
socket.on('iot-update', (data) => {
  updateDashboard(data);
  updateSliders(data);
});

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
    const res = await fetch(`${API_BASE}/set-scenario`, {
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
    await fetch(`${API_BASE}/reset`, { method: 'POST' });
  } catch (e) {
    console.error(e);
  }
}

async function startSimulation() {
  const interval = parseInt(document.getElementById('sim-interval').value) || 2000;
  try {
    const res = await fetch(`${API_BASE}/simulate`, {
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
    const res = await fetch(`${API_BASE}/stop-simulation`, { method: 'POST' });
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
      
      await fetch(`${API_BASE}/update-iot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch (e) {
      console.error(e);
    }
  }, 100);
}
