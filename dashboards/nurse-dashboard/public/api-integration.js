/**
 * Nurse Dashboard Vanilla JS API Integration Script
 * 
 * Provides infant location polling with audio alerts for EXIT zones.
 */
(function() {
  'use strict';

  // API Configuration
  const API_BASE = window.API_GATEWAY || '/api/v1';
  const LOCATION_POLL_INTERVAL = 2000; // ms
  const FETCH_TIMEOUT = 8000; // ms

  // State
  let infants = [];
  let locationPollers = new Map();
  let audioContext = null;
  let audioResumed = false;

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
    console.warn('[Nurse API] CORS/Network Error:', message);
  }

  function hideCORSError() {
    const errorEl = document.getElementById('cors-error') || document.getElementById('api-error');
    if (errorEl) {
      errorEl.style.display = 'none';
    }
  }

  // =============================================================================
  // Audio Alert (Web Audio API)
  // =============================================================================

  function initAudioContext() {
    if (audioContext) return;
    try {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      if (audioContext.state === 'suspended') {
        const resumeAudio = () => {
          if (!audioResumed && audioContext.state === 'suspended') {
            audioContext.resume().then(() => {
              audioResumed = true;
            }).catch(() => {});
          }
        };
        document.addEventListener('click', resumeAudio, { once: true });
        document.addEventListener('keydown', resumeAudio, { once: true });
      } else {
        audioResumed = true;
      }
    } catch (e) {
      console.warn('[Nurse API] Web Audio API not supported');
    }
  }

  function playBeep() {
    if (!audioContext || audioContext.state !== 'running') {
      initAudioContext();
      if (!audioContext || audioContext.state !== 'running') return;
    }
    try {
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(880, audioContext.currentTime);
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.3);
    } catch (e) {
      // Silently fail if autoplay blocked
    }
  }

  // =============================================================================
  // API Calls
  // =============================================================================

  async function fetchInfants() {
    try {
      const controller = createAbortController();
      const response = await fetch(`${API_BASE}/infants/`, {
        signal: controller.signal,
        headers: { 'Accept': 'application/json' }
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      hideCORSError();
      return data.items || [];
    } catch (error) {
      if (isCORSError(error)) {
        showCORSError('Failed to fetch infants. Check CORS configuration.');
      } else {
        console.warn('[Nurse API] fetchInfants error:', error.message);
      }
      return [];
    }
  }

  async function fetchInfantLocation(infantId) {
    try {
      const controller = createAbortController();
      const response = await fetch(`${API_BASE}/rtls/tags/${infantId}/latest`, {
        signal: controller.signal,
        headers: { 'Accept': 'application/json' }
      });

      if (response.status === 404) return null;
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      return await response.json();
    } catch (error) {
      if (isCORSError(error)) {
        console.warn(`[Nurse API] Location fetch CORS error for ${infantId}`);
      }
      return null;
    }
  }

  // =============================================================================
  // DOM Updates
  // =============================================================================

  function updateInfantDOM(infant, location) {
    const container = document.querySelector(`[data-infant-id="${infant.id}"]`) ||
                      document.querySelector(`[data-infant-id="${infant.tag_id}"]`);

    if (!container) return;

    const hospitalNoEl = container.querySelector('.hospital_infant_no');
    if (hospitalNoEl) {
      hospitalNoEl.textContent = infant.tag_id || infant.hospital_infant_no || '';
    }

    const zoneNameEl = container.querySelector('.zone_name');
    if (zoneNameEl && location) {
      zoneNameEl.textContent = location.zone_name || location.floor || 'Unknown';
    }

    if (location && location.zone_type === 'EXIT') {
      playBeep();
      container.classList.add('exit-zone-alert');
    } else {
      container.classList.remove('exit-zone-alert');
    }
  }

  // =============================================================================
  // Polling Logic
  // =============================================================================

  function startLocationPolling(infant) {
    if (locationPollers.has(infant.id)) return;

    let pending = false;

    const poll = async () => {
      if (pending) return;
      pending = true;
      try {
        const location = await fetchInfantLocation(infant.tag_id);
        updateInfantDOM(infant, location);
      } finally {
        pending = false;
      }
    };

    poll();
    const intervalId = setInterval(poll, LOCATION_POLL_INTERVAL);
    locationPollers.set(infant.id, intervalId);
  }

  function stopAllPolling() {
    locationPollers.forEach((intervalId) => clearInterval(intervalId));
    locationPollers.clear();
  }

  async function initNurseDashboard() {
    initAudioContext();

    infants = await fetchInfants();

    if (infants.length === 0) {
      console.log('[Nurse API] No infants found or API unavailable');
      return;
    }

    console.log(`[Nurse API] Loaded ${infants.length} infants, starting location polling`);
    infants.forEach(infant => startLocationPolling(infant));
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
    setTimeout(initNurseDashboard, 500);
  });

  window.addEventListener('beforeunload', stopAllPolling);
  window.addEventListener('unload', stopAllPolling);

})();
