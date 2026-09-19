/* ══════════════════════════════════════════════════
   MadhuSathi IoT Hive Command Centre — Dashboard JS
═══════════════════════════════════════════════════ */
const socket = io();
const API_BASE = '/api/v1';

let hives = {};           // { hiveId: stateObject }
let simRunning = {};      // { hiveId: true/false }
let modalHiveId = null;   // which hive is open in the modal
let modalUpdateTimer = null;

// ─────────────────────────────────────────────────
// Socket: receive initial snapshot of all hives
// ─────────────────────────────────────────────────
socket.on('initial-data', (dataArray) => {
  hives = {};
  dataArray.forEach(item => {
    hives[item.hiveId] = item.data;
  });
  renderAllCards();
  updateGlobalStats();
});

// ─────────────────────────────────────────────────
// Socket: live update for a single hive
// ─────────────────────────────────────────────────
socket.on('iot-update', (payload) => {
  const hiveId = payload.hiveId || 'HIVE_001';
  const data   = payload.data   || payload;

  hives[hiveId] = data;

  // If card doesn't exist yet, create it
  if (!document.getElementById(`card-${hiveId}`)) {
    renderCard(hiveId, data);
  } else {
    updateCard(hiveId, data);
  }

  updateGlobalStats();

  // If this hive's modal is open, refresh the modal too
  if (modalHiveId === hiveId) {
    populateModal(hiveId, data);
  }
});

// ─────────────────────────────────────────────────
// Render all hive cards from scratch
// ─────────────────────────────────────────────────
function renderAllCards() {
  const grid = document.getElementById('hive-grid');
  grid.innerHTML = '';

  const ids = Object.keys(hives);
  if (ids.length === 0) {
    grid.innerHTML = `
      <div class="empty-state" id="empty-state">
        <div class="empty-icon">🍯</div>
        <div>No hives registered yet. Add one above.</div>
      </div>`;
    return;
  }

  ids.forEach(id => renderCard(id, hives[id]));
}

// ─────────────────────────────────────────────────
// Create a hive card DOM element and append to grid
// ─────────────────────────────────────────────────
function renderCard(hiveId, data) {
  // Remove empty state placeholder if present
  const empty = document.getElementById('empty-state');
  if (empty) empty.remove();

  const grid = document.getElementById('hive-grid');
  const card = document.createElement('div');
  card.className = 'hive-card';
  card.id = `card-${hiveId}`;
  card.setAttribute('data-status', data.status || 'Healthy');
  card.innerHTML = cardHTML(hiveId, data);
  grid.appendChild(card);
}

// ─────────────────────────────────────────────────
// Update an existing hive card in place
// ─────────────────────────────────────────────────
function updateCard(hiveId, data) {
  const card = document.getElementById(`card-${hiveId}`);
  if (!card) return;
  card.setAttribute('data-status', data.status || 'Healthy');
  card.innerHTML = cardHTML(hiveId, data);
}

// ─────────────────────────────────────────────────
// Generate inner HTML for a hive card
// ─────────────────────────────────────────────────
function cardHTML(hiveId, data) {
  const isRunning = !!simRunning[hiveId];
  const ts = data.last_updated || data.timestamp;
  const timeStr = ts ? new Date(ts).toLocaleTimeString() : '--';

  return `
    <div class="card-header">
      <div class="card-hive-id">${hiveId}</div>
      <div class="card-badges">
        <span class="badge ${data.status || ''}">${data.status || '--'}</span>
        <span class="badge ${data.activity_level || ''}">${data.activity_level || '--'}</span>
      </div>
    </div>
    <div class="card-metrics">
      <div class="card-metric">
        <div class="cm-label">Temp</div>
        <div class="cm-val">${fmtNum(data.temperature, 1)}<span class="cm-unit"> °C</span></div>
      </div>
      <div class="card-metric">
        <div class="cm-label">Humidity</div>
        <div class="cm-val">${fmtNum(data.humidity, 1)}<span class="cm-unit"> %</span></div>
      </div>
      <div class="card-metric">
        <div class="cm-label">Weight</div>
        <div class="cm-val">${fmtNum(data.weight, 1)}<span class="cm-unit"> kg</span></div>
      </div>
      <div class="card-metric">
        <div class="cm-label">Sound</div>
        <div class="cm-val">${fmtNum(data.sound_level, 1)}<span class="cm-unit"> dB</span></div>
      </div>
      <div class="card-metric">
        <div class="cm-label">CO₂</div>
        <div class="cm-val">${Math.round(data.co2_level || 0)}<span class="cm-unit"> ppm</span></div>
      </div>
    </div>
    <div class="card-footer">
      <div class="sim-indicator">
        <div class="sim-dot ${isRunning ? 'running' : ''}"></div>
        ${isRunning ? 'Simulating' : 'Idle'}
      </div>
      <div style="font-size:0.68rem;color:var(--text-muted)">${timeStr}</div>
      <button class="card-open-btn" onclick="openModal('${hiveId}', event)">Configure →</button>
    </div>`;
}

// ─────────────────────────────────────────────────
// Global Stats Bar (top of page)
// ─────────────────────────────────────────────────
function updateGlobalStats() {
  let healthy = 0, warning = 0, critical = 0;
  const ids = Object.keys(hives);

  ids.forEach(id => {
    const s = hives[id].status;
    if (s === 'Healthy')  healthy++;
    else if (s === 'Warning')  warning++;
    else if (s === 'Critical') critical++;
  });

  document.getElementById('stat-healthy').textContent  = healthy;
  document.getElementById('stat-warning').textContent  = warning;
  document.getElementById('stat-critical').textContent = critical;
  document.getElementById('stat-total').textContent    = ids.length;
}

// ─────────────────────────────────────────────────
// Register a new hive
// ─────────────────────────────────────────────────
async function registerHive() {
  const input  = document.getElementById('new-hive-id');
  const hiveId = input.value.trim().toUpperCase();
  if (!hiveId) return showToast('Enter a Hive ID first', 'warn');

  try {
    const res  = await fetch(`${API_BASE}/register-hive`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ hiveId })
    });
    const json = await res.json();
    if (json.success) {
      input.value = '';
      showToast(`${hiveId} registered!`);
    } else {
      showToast(json.error, 'warn');
    }
  } catch (e) {
    showToast('Registration failed', 'error');
    console.error(e);
  }
}

// ─────────────────────────────────────────────────
// Modal: open for a specific hive
// ─────────────────────────────────────────────────
function openModal(hiveId, evt) {
  if (evt) evt.stopPropagation();
  modalHiveId = hiveId;
  const data  = hives[hiveId] || {};

  document.getElementById('modal-hive-id').textContent = hiveId;
  populateModal(hiveId, data);
  updateModalSimStatus(hiveId);

  document.getElementById('modal-backdrop').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  modalHiveId = null;
  document.getElementById('modal-backdrop').classList.remove('open');
  document.body.style.overflow = '';
}

// ─────────────────────────────────────────────────
// Modal: populate with fresh data
// ─────────────────────────────────────────────────
function populateModal(hiveId, data) {
  // Status badges
  setModalBadge('modal-status-badge',   data.status);
  setModalBadge('modal-activity-badge', data.activity_level);

  // Timestamp
  const ts = data.last_updated || data.timestamp;
  document.getElementById('modal-timestamp').textContent =
    ts ? new Date(ts).toLocaleTimeString() : '--';

  // Metric tiles
  document.getElementById('m-temp').textContent   = fmtNum(data.temperature, 1);
  document.getElementById('m-hum').textContent    = fmtNum(data.humidity, 1);
  document.getElementById('m-weight').textContent = fmtNum(data.weight, 1);
  document.getElementById('m-sound').textContent  = fmtNum(data.sound_level, 1);
  document.getElementById('m-co2').textContent    = Math.round(data.co2_level || 0);

  // Sliders — only update if no user is dragging (check focus)
  const sliderIds = [
    ['m-slider-temp',   'm-slide-val-temp',   data.temperature,  1],
    ['m-slider-hum',    'm-slide-val-hum',    data.humidity,     1],
    ['m-slider-weight', 'm-slide-val-weight', data.weight,       1],
    ['m-slider-sound',  'm-slide-val-sound',  data.sound_level,  1],
    ['m-slider-co2',    'm-slide-val-co2',    data.co2_level,    0],
  ];
  sliderIds.forEach(([sliderId, valId, value, decimals]) => {
    const el = document.getElementById(sliderId);
    if (el && document.activeElement !== el) {
      el.value = value;
      const span = document.getElementById(valId);
      if (span) span.textContent = decimals ? parseFloat(value).toFixed(decimals) : Math.round(value);
    }
  });
}

function setModalBadge(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent  = value || '--';
  el.className = 'badge ' + (value || '');
}

function updateModalSimStatus(hiveId) {
  const el = document.getElementById('modal-sim-status');
  if (!el) return;
  if (simRunning[hiveId]) {
    el.textContent = 'Simulation running…';
    el.style.color = '#3fb950';
  } else {
    el.textContent = 'Idle';
    el.style.color = '';
  }
}

// ─────────────────────────────────────────────────
// Modal actions — single hive
// ─────────────────────────────────────────────────
async function modalScenario(scenario) {
  if (!modalHiveId) return;
  await applyScenario(modalHiveId, scenario);
}

async function modalReset() {
  if (!modalHiveId) return;
  await resetHive(modalHiveId);
}

async function modalStartSim() {
  if (!modalHiveId) return;
  const interval = parseInt(document.getElementById('modal-sim-interval').value) || 2000;
  const ok = await startSim(modalHiveId, interval);
  if (ok) {
    simRunning[modalHiveId] = true;
    updateModalSimStatus(modalHiveId);
    updateCard(modalHiveId, hives[modalHiveId]);
  }
}

async function modalStopSim() {
  if (!modalHiveId) return;
  const ok = await stopSim(modalHiveId);
  if (ok) {
    simRunning[modalHiveId] = false;
    updateModalSimStatus(modalHiveId);
    updateCard(modalHiveId, hives[modalHiveId]);
  }
}

let modalSliderTimer = null;
function modalUpdateValue(field, value) {
  // Update label immediately
  const key = field.split('_')[0];
  const span = document.getElementById(`m-slide-val-${key}`);
  if (span) span.textContent = field === 'co2_level'
    ? Math.round(parseFloat(value))
    : parseFloat(value).toFixed(1);

  clearTimeout(modalSliderTimer);
  modalSliderTimer = setTimeout(async () => {
    if (!modalHiveId) return;
    const payload = {};
    payload[field] = parseFloat(value);
    try {
      await fetch(`${API_BASE}/update-iot/${modalHiveId}`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload)
      });
    } catch (e) { console.error(e); }
  }, 120);
}

// ─────────────────────────────────────────────────
// Fleet (All-hive) actions
// ─────────────────────────────────────────────────
async function fleetSimulateAll() {
  const interval = parseInt(document.getElementById('global-interval').value) || 2000;
  try {
    const res  = await fetch(`${API_BASE}/simulate-all`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ interval })
    });
    const json = await res.json();
    if (json.success) {
      Object.keys(hives).forEach(id => { simRunning[id] = true; });
      Object.keys(hives).forEach(id => updateCard(id, hives[id]));
      showToast(`Simulation started for ${json.data.startedCount} hives`);
    } else {
      showToast(json.error, 'warn');
    }
  } catch (e) { console.error(e); showToast('Fleet simulate failed', 'error'); }
}

async function fleetStopAll() {
  try {
    const res  = await fetch(`${API_BASE}/stop-simulation-all`, { method: 'POST' });
    const json = await res.json();
    if (json.success) {
      Object.keys(hives).forEach(id => { simRunning[id] = false; });
      Object.keys(hives).forEach(id => updateCard(id, hives[id]));
      showToast(`Stopped ${json.data.stoppedCount} simulations`);
    }
  } catch (e) { console.error(e); showToast('Fleet stop failed', 'error'); }
}

async function fleetScenario(scenario) {
  const ids = Object.keys(hives);
  if (ids.length === 0) return showToast('No hives registered', 'warn');
  let count = 0;
  for (const id of ids) {
    const ok = await applyScenario(id, scenario);
    if (ok) count++;
  }
  showToast(`"${scenario}" applied to ${count} hives`);
}

async function fleetReset() {
  const ids = Object.keys(hives);
  if (ids.length === 0) return showToast('No hives registered', 'warn');
  for (const id of ids) await resetHive(id);
  showToast(`Reset ${ids.length} hives to default`);
}

// ─────────────────────────────────────────────────
// Shared API helpers
// ─────────────────────────────────────────────────
async function applyScenario(hiveId, scenario) {
  try {
    const res  = await fetch(`${API_BASE}/set-scenario/${hiveId}`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ scenario })
    });
    const json = await res.json();
    if (!json.success) showToast(json.error, 'warn');
    return json.success;
  } catch (e) { console.error(e); return false; }
}

async function resetHive(hiveId) {
  try {
    const res  = await fetch(`${API_BASE}/reset/${hiveId}`, { method: 'POST' });
    const json = await res.json();
    return json.success;
  } catch (e) { console.error(e); return false; }
}

async function startSim(hiveId, interval) {
  try {
    const res  = await fetch(`${API_BASE}/simulate/${hiveId}`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ interval })
    });
    const json = await res.json();
    if (!json.success) showToast(json.error, 'warn');
    return json.success;
  } catch (e) { console.error(e); return false; }
}

async function stopSim(hiveId) {
  try {
    const res  = await fetch(`${API_BASE}/stop-simulation/${hiveId}`, { method: 'POST' });
    const json = await res.json();
    if (!json.success) showToast(json.error, 'warn');
    return json.success;
  } catch (e) { console.error(e); return false; }
}

// ─────────────────────────────────────────────────
// Toast notification
// ─────────────────────────────────────────────────
let toastTimer;
function showToast(msg, type) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.style.borderColor = type === 'warn'  ? 'var(--warning)'
                        : type === 'error' ? 'var(--critical)'
                        : 'var(--healthy)';
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 3000);
}

// ─────────────────────────────────────────────────
// Utility: format number
// ─────────────────────────────────────────────────
function fmtNum(val, dec) {
  const n = parseFloat(val);
  return isNaN(n) ? '--' : n.toFixed(dec);
}

// ─────────────────────────────────────────────────
// Keyboard: Escape closes modal
// ─────────────────────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});
