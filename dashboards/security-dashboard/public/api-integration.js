/**
 * Security Dashboard Vanilla JS API Integration Script
 * 
 * Provides polling for alarms and gate events, plus silence button handling.
 */
(function() {
  'use strict';

  // API Configuration
  const API_BASE = window.API_GATEWAY || '/api/v1';
  const ALARM_POLL_INTERVAL = 1000; // 1 second
  const GATE_POLL_INTERVAL = 3000; // 3 seconds
  const FETCH_TIMEOUT = 8000; // ms

  // State
  let alarmPollerId = null;
  let gatePollerId = null;
  let alarmPending = false;
  let gatePending = false;
  let silenceInFlight = false;

  // =============================================================================
  // Utility Functions
  // =============================================================================

  function createAbortController() {
    const controller = new AbortController();
    setTimeout(() => controller.abort(), FETCH_TIMEOUT);
    return controller;
  }

  function isCORSError(error) {
    return error instanceof TypeError || (error.message && error.message.includes('Failed to fetch'));
  }

  function showCORSError(message) {
    const errorEl = document.getElementById('cors-error') || document.getElementById('api-error');
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.style.display = 'block';
    }
    console.warn('[Security API] CORS/Network Error:', message);
  }

  function hideCORSError() {
    const errorEl = document.getElementById('cors-error') || document.getElementById('api-error');
    if (errorEl) {
      errorEl.style.display = 'none';
    }
  }

  // =============================================================================
  // API Calls
  // =============================================================================

  // Fetch alarm status
  async function fetchAlarmStatus() {
    try {
      const controller = createAbortController();
      const response = await fetch(`${API_BASE}/alerts?acknowledged=false`, {
        signal: controller.signal,
        headers: { 'Accept': 'application/json' }
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      hideCORSError();
      return data.items || [];
    } catch (error) {
      if (isCORSError(error)) {
        showCORSError('Failed to fetch alarm status. Check CORS configuration.');
      } else {
        console.warn('[Security API] fetchAlarmStatus error:', error.message);
      }
      return [];
    }
  }

  // Silence alarm
  async function silenceAlarm() {
    if (silenceInFlight) return false;
    silenceInFlight = true;

    const silenceBtn = document.getElementById('silence-btn') || document.querySelector('.silence-btn');
    if (silenceBtn) silenceBtn.disabled = true;

    try {
      const controller = createAbortController();
      const response = await fetch(`${API_BASE}/alerts/silence`, {
        method: 'POST',
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({})
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const statusEl = document.getElementById('silence-status');
      if (statusEl) {
        statusEl.textContent = 'Alarm silenced successfully';
        setTimeout(() => { statusEl.textContent = ''; }, 3000);
      }
      console.log('[Security API] Alarm silenced');
      return true;
    } catch (error) {
      console.warn('[Security API] silenceAlarm error:', error.message);
      return false;
    } finally {
      silenceInFlight = false;
      if (silenceBtn) silenceBtn.disabled = false;
    }
  }

  // Fetch gate movements
  async function fetchGateMovements() {
    try {
      const controller = createAbortController();
      const response = await fetch(`${API_BASE}/gates/events/latest`, {
        signal: controller.signal,
        headers: { 'Accept': 'application/json' }
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      return data.items || [];
    } catch (error) {
      if (isCORSError(error)) {
        console.warn('[Security API] Gate movements fetch CORS error');
      }
      return [];
    }
  }

  // =============================================================================
  // DOM Updates
  // =============================================================================

  function updateAlarmOverlay(alarms) {
    const overlay = document.getElementById('alarm-overlay') || document.querySelector('.alarm-overlay');
    if (!overlay) return;

    if (alarms.length === 0) {
      overlay.style.display = 'none';
      return;
    }

    overlay.style.display = 'flex';

    const zoneIdEl = document.getElementById('alarm-zone-id');
    if (zoneIdEl) {
      const zoneIds = alarms
        .map(a => a.extra_data?.zone_id || a.zone_id || a.tag_id || 'Unknown')
        .join(', ');
      zoneIdEl.textContent = `Zone: ${zoneIds}`;
    }
  }

  function updateGateLog(events) {
    const gateLog = document.getElementById('gate-log') || document.querySelector('.gate-log');
    if (!gateLog) return;

    gateLog.innerHTML = '';

    events.slice(0, 20).forEach(event => {
      const li = document.createElement('li');
      const timestamp = event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : '';
      const gateId = event.gate_id || event.zone || 'Unknown';
      const result = event.result || event.event_type || '';
      const resultClass = result === 'DENIED' ? 'text-red-400' : 'text-green-400';

      li.innerHTML = `
        <span class="text-slate-400">${timestamp}</span>
        <span class="mx-2">${gateId}</span>
        <span class="${resultClass}">${result}</span>
      `;
      li.className = 'flex items-center gap-2 py-1 text-sm';
      gateLog.appendChild(li);
    });
  }

  // =============================================================================
  // Polling Logic
  // =============================================================================

  async function pollAlarms() {
    if (alarmPending) return;
    alarmPending = true;
    try {
      const alarms = await fetchAlarmStatus();
      updateAlarmOverlay(alarms);
    } finally {
      alarmPending = false;
    }
  }

  async function pollGateMovements() {
    if (gatePending) return;
    gatePending = true;
    try {
      const events = await fetchGateMovements();
      updateGateLog(events);
    } finally {
      gatePending = false;
    }
  }

  function startPolling() {
    pollAlarms();
    alarmPollerId = setInterval(pollAlarms, ALARM_POLL_INTERVAL);

    pollGateMovements();
    gatePollerId = setInterval(pollGateMovements, GATE_POLL_INTERVAL);
  }

  function stopPolling() {
    if (alarmPollerId) clearInterval(alarmPollerId);
    if (gatePollerId) clearInterval(gatePollerId);
    alarmPollerId = null;
    gatePollerId = null;
  }

  // =============================================================================
  // Event Bindings
  // =============================================================================

  function bindSilenceButton() {
    const silenceBtn = document.getElementById('silence-btn') || document.querySelector('.silence-btn');
    if (silenceBtn) {
      silenceBtn.addEventListener('click', silenceAlarm);
    }
  }

  // =============================================================================
  // Initialization
  // =============================================================================

  function onDOMReady(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  }

  onDOMReady(() => {
    setTimeout(() => {
      bindSilenceButton();
      startPolling();
      console.log('[Security API] Initialized - polling alarms every 1s, gates every 3s');
    }, 500);
  });

  window.addEventListener('beforeunload', stopPolling);
  window.addEventListener('unload', stopPolling);

})();
