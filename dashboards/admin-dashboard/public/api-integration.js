/**
 * Admin Dashboard Vanilla JS API Integration Script
 * 
 * Provides device polling with battery status display.
 */
(function() {
  'use strict';

  // API Configuration
  const API_BASE = window.API_GATEWAY || '/api/v1';
  const DEVICE_POLL_INTERVAL = 5000; // 5 seconds
  const FETCH_TIMEOUT = 8000; // ms

  // State
  let devicePollerId = null;
  let devicePending = false;

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
    console.warn('[Admin API] CORS/Network Error:', message);
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

  async function fetchDevices() {
    try {
      const controller = createAbortController();
      const response = await fetch(`${API_BASE}/rtls/tags`, {
        signal: controller.signal,
        headers: { 'Accept': 'application/json' }
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      hideCORSError();
      return Array.isArray(data) ? data : (data.items || []);
    } catch (error) {
      if (isCORSError(error)) {
        showCORSError('Failed to fetch devices. Check CORS configuration.');
      } else {
        console.warn('[Admin API] fetchDevices error:', error.message);
      }
      return [];
    }
  }

  // =============================================================================
  // DOM Updates
  // =============================================================================

  function updateDevicesTable(devices) {
    const tbody = document.getElementById('devices-tbody') ||
                  document.querySelector('.devices-tbody') ||
                  document.querySelector('table tbody');

    if (!tbody) return;

    tbody.innerHTML = '';

    devices.forEach(device => {
      const tr = document.createElement('tr');

      const deviceType = device.device_type || device.asset_type || 'tag';
      const serialNumber = device.serial_number || device.tag_id || device.id || 'N/A';
      const battery = device.battery || device.battery_pct || 100;

      if (battery < 20) {
        tr.classList.add('low-battery');
      }

      tr.innerHTML = `
        <td class="px-4 py-3 text-sm">${deviceType}</td>
        <td class="px-4 py-3 text-sm font-mono">${serialNumber}</td>
        <td class="px-4 py-3 text-sm">
          <span class="${battery < 20 ? 'text-red-400' : battery < 50 ? 'text-yellow-400' : 'text-green-400'}">
            ${battery}%
          </span>
        </td>
      `;

      tbody.appendChild(tr);
    });

    if (devices.length === 0) {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td colspan="3" class="px-4 py-8 text-center text-slate-400">
          No devices found
        </td>
      `;
      tbody.appendChild(tr);
    }
  }

  // =============================================================================
  // Polling Logic
  // =============================================================================

  async function pollDevices() {
    if (devicePending) return;
    devicePending = true;
    try {
      const devices = await fetchDevices();
      updateDevicesTable(devices);
    } finally {
      devicePending = false;
    }
  }

  function startPolling() {
    pollDevices();
    devicePollerId = setInterval(pollDevices, DEVICE_POLL_INTERVAL);
    console.log('[Admin API] Initialized - polling devices every 5s');
  }

  function stopPolling() {
    if (devicePollerId) clearInterval(devicePollerId);
    devicePollerId = null;
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
    setTimeout(startPolling, 500);
  });

  window.addEventListener('beforeunload', stopPolling);
  window.addEventListener('unload', stopPolling);

})();
