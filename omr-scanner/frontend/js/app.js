/**
 * app.js
 * ------
 * Wires the camera/quality/guidance modules to the DOM: view routing,
 * HUD drawing, the batch-scanning workflow (queue, running stats,
 * seamless return to camera after each successful scan), and the
 * confidence-aware result screen sourced from /api/scan.
 */
(() => {
  const $ = (sel) => document.querySelector(sel);

  const views = {
    home: $('#view-home'),
    camera: $('#view-camera'),
    processing: $('#view-processing'),
    result: $('#view-result'),
    summary: $('#view-summary'),
  };
  function showView(name) {
    Object.values(views).forEach(v => v.classList.remove('is-active'));
    views[name].classList.add('is-active');
  }

  const state = {
    sessionId: null,
    sheetsScanned: 0,
    results: [],
    lastCaptureBlob: null,
    lastSheetLabel: null,
    camera: null,
    stability: null,
    capturing: false,
    cameraToken: 0,  // bumped on every openCamera()/closeCamera() to detect stale async work
  };

  // ---------------- config ----------------
  async function loadConfig() {
    try {
      const res = await fetch('/api/config');
      const cfg = await res.json();
      OMRQuality.setTargetAspect(cfg.target_aspect);
    } catch (e) {
      console.warn('Could not load /api/config, using default aspect ratio', e);
    }
  }

  // ---------------- session/stats ----------------
  async function ensureSession() {
    if (state.sessionId) return state.sessionId;
    const res = await fetch('/api/session', { method: 'POST' });
    const data = await res.json();
    state.sessionId = data.session_id;
    return state.sessionId;
  }

  function refreshHomeStats() {
    const card = $('#session-card');
    if (state.sheetsScanned === 0) { card.hidden = true; return; }
    card.hidden = false;
    $('#stat-scanned').textContent = state.sheetsScanned;
    const avg = state.results.length
      ? (state.results.reduce((s, r) => s + r.avg_confidence, 0) / state.results.length)
      : 0;
    $('#stat-avgconf').textContent = state.results.length ? `${avg.toFixed(0)}%` : '—';
    $('#stat-retakes').textContent = state.results.filter(r => r.retake_recommended).length;
  }

  // ---------------- HUD drawing ----------------
  function drawHud(metrics, verdict) {
    const quadEl = $('#hud-quad');
    const cornersEl = $('#hud-corners');
    if (!metrics.sheetFound || !metrics.quad) {
      quadEl.classList.add('is-hidden');
      cornersEl.innerHTML = '';
      return;
    }
    quadEl.classList.remove('is-hidden');
    const fw = metrics.frameW, fh = metrics.frameH;
    const pts = metrics.quad.map(p => `${(p.x / fw) * 100},${(p.y / fh) * 100}`).join(' ');
    quadEl.setAttribute('points', pts);
    quadEl.dataset.state = verdict.state === 'ready' ? 'ready' : (verdict.state === 'error' ? 'error' : 'warn');
    cornersEl.innerHTML = metrics.quad.map(p => {
      const x = (p.x / fw) * 100, y = (p.y / fh) * 100;
      return `<line class="hud-corner-tick" x1="${x - 3}" y1="${y}" x2="${x + 3}" y2="${y}" />
              <line class="hud-corner-tick" x1="${x}" y1="${y - 3}" x2="${x}" y2="${y + 3}" />`;
    }).join('');
  }

  function setStatus(verdict) {
    const banner = $('#status-banner');
    banner.dataset.state = verdict.state === 'ready' ? 'ready' : (verdict.code === 'not_found' ? 'searching' : 'warn');
    $('#status-text').textContent = verdict.message;
    $('#status-detail').textContent = verdict.detail || '';
  }

  function setRing(progress) {
    const circumference = 119.4;
    $('#ring-fill').style.strokeDashoffset = String(circumference * (1 - progress));
  }

  // ---------------- camera flow ----------------
  // Guards openCamera() against overlapping invocations (e.g. fast double-tap).
  let openingCamera = false;

  async function openCamera() {
    if (openingCamera) return;
    openingCamera = true;
    const myToken = ++state.cameraToken;
    try {
      showView('camera');
      $('#status-text').textContent = 'Starting camera…';
      $('#status-banner').dataset.state = 'searching';
      $('#batch-count').textContent = state.sheetsScanned;

      await ensureSession();

      const video = $('#video');
      const analyzeCanvas = $('#canvas-analyze');
      const captureCanvas = $('#canvas-capture');
      const cam = new OMRCapture.CameraSession(video, analyzeCanvas, captureCanvas);

      try {
        await cam.start();
      } catch (e) {
        if (myToken !== state.cameraToken) { cam.stop(); return; }
        $('#status-text').textContent = 'Camera access failed';
        $('#status-detail').textContent = e.message || String(e);
        $('#status-banner').dataset.state = 'error';
        return;
      }

      if (myToken !== state.cameraToken) { cam.stop(); return; }

      state.camera = cam;
      state.capturing = false;
      state.stability = new OMRGuidance.StabilityTracker(() => triggerCapture(cam, myToken));

      cam.onStreamEnded = () => {
        if (myToken !== state.cameraToken) return;
        state.capturing = false;
        if (state.stability) state.stability.reset();
        $('#status-banner').dataset.state = 'error';
        $('#status-text').textContent = 'Camera disconnected';
        $('#status-detail').textContent = 'The camera stream stopped unexpectedly — close and reopen to continue.';
      };

      cam.runAnalysisLoop((metrics, verdict) => {
        if (myToken !== state.cameraToken || state.capturing) return;
        drawHud(metrics, verdict);
        setStatus(verdict);
        const progress = state.stability.update(metrics, verdict);
        setRing(progress);
      });
    } finally {
      openingCamera = false;
    }
  }

  // Pause camera when the tab is backgrounded (saves battery, avoids
  // holding hardware while the user isn't looking).
  let wasInCameraViewOnHide = false;
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      wasInCameraViewOnHide = views.camera.classList.contains('is-active') && !!state.camera;
      if (state.camera) { state.camera.stop(); state.camera = null; }
      if (state.stability) state.stability.reset();
    } else if (wasInCameraViewOnHide && !state.capturing) {
      wasInCameraViewOnHide = false;
      openCamera();
    }
  });

  function closeCamera() {
    state.cameraToken++;
    if (state.camera) state.camera.stop();
    state.camera = null;
    state.stability = null;
    showView('home');
    refreshHomeStats();
  }

  async function flash() {
    const el = $('#capture-flash');
    el.classList.add('is-flashing');
    await new Promise(r => setTimeout(r, 90));
    el.classList.remove('is-flashing');
  }

  async function triggerCapture(cam, token) {
    if (state.capturing || !state.camera || token !== state.cameraToken) return;
    state.capturing = true;
    const stale = () => token !== state.cameraToken;

    try {
      await cam.lockForCapture();
      if (stale()) return;
      await flash();
      if (stale()) return;
      const canvas = await cam.grabFullResFrame();
      if (stale()) return;

      showView('processing');
      $('#processing-title').textContent = 'Checking image quality…';
      $('#processing-sub').textContent = 'Validating corners, sharpness and lighting before upload';

      await new Promise(r => setTimeout(r, 60));
      if (stale()) return;
      const validation = cam.validateFullRes(canvas);
      await cam.unlockAfterCapture();
      if (stale()) return;

      if (!validation.pass) {
        state.capturing = false;
        state.stability.reset();
        showView('camera');
        $('#status-banner').dataset.state = 'error';
        $('#status-text').textContent = 'Retake needed: ' + validation.reasons[0];
        $('#status-detail').textContent = validation.reasons.slice(1).join(' · ');
        return;
      }

      $('#processing-title').textContent = 'Uploading sheet…';
      $('#processing-sub').textContent = 'Running alignment and bubble detection';

      const blob = await OMRCapture.compressCanvas(canvas);
      const sheetLabel = `Sheet ${state.sheetsScanned + 1}`;
      const result = await OMRCapture.uploadSheet(blob, { sessionId: state.sessionId, sheetLabel });
      if (stale()) return;

      if (window.OMR_DEBUG === true || (() => { try { return localStorage.getItem('omrDebug') === '1'; } catch (e) { return false; } })()) {
        console.log('[OMR] scan result', {
          templateValid: result.template_valid,
          templateMatch: result.template_match,
          avgConfidence: result.avg_confidence,
          flagged: result.flagged_count,
          retake: result.retake_recommended,
          backendMs: result.processing_ms,
        });
      }

      state.sheetsScanned += 1;
      state.results.push(result);
      renderResult(result);
      showView('result');
    } catch (e) {
      if (stale()) return;
      state.capturing = false;
      if (state.stability) state.stability.reset();
      showView('camera');
      $('#status-banner').dataset.state = 'error';
      $('#status-text').textContent = 'Capture failed — try again';
      $('#status-detail').textContent = e.message || String(e);
    }
  }

  // ---------------- result screen ----------------
  function renderResult(result) {
    const badge = $('#result-badge');
    const icon = $('#result-icon');
    const title = $('#result-title');
    const sub = $('#result-sub');
    const notes = $('#result-notes');
    const flaggedList = $('#flagged-list');

    $('#metric-confidence').textContent = `${result.avg_confidence.toFixed(0)}%`;
    $('#metric-flagged').textContent = result.flagged_count;
    $('#metric-label').textContent = state.sheetsScanned;

    if (result.retake_recommended) {
      badge.dataset.state = 'warn';
      icon.innerHTML = '<path d="M12 3 2 21h20L12 3z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><line x1="12" y1="9" x2="12" y2="14" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="17.5" r="1.1" fill="currentColor"/>';
      title.textContent = 'Retake recommended';
      // A failed post-correction template match is the more fundamental
      // reason to retake than a low confidence average, so lead with it.
      if (result.template_valid === false) {
        const pct = result.template_match != null ? ` (${Math.round(result.template_match)}% template match)` : '';
        sub.textContent = `Captured sheet didn\u2019t match the template layout${pct} — realign and retake`;
      } else {
        sub.textContent = `Confidence ${result.avg_confidence.toFixed(0)}% — below the accuracy threshold`;
      }
    } else {
      badge.dataset.state = 'ok';
      icon.innerHTML = '<path d="M5 13l4 4L19 7" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>';
      title.textContent = 'Scan complete';
      sub.textContent = `Confidence ${result.avg_confidence.toFixed(0)}% · ${result.flagged_count} question${result.flagged_count === 1 ? '' : 's'} flagged`;
    }

    if (result.sheet_notes && result.sheet_notes.length) {
      notes.textContent = result.sheet_notes.join(' · ');
      notes.classList.add('is-visible');
    } else {
      notes.classList.remove('is-visible');
    }

    if (result.flagged_questions && result.flagged_questions.length) {
      flaggedList.innerHTML = result.flagged_questions.map(fq => `
        <div class="flagged-row">
          <span>Question ${fq.question}${fq.notes ? ' — ' + fq.notes : ''}</span>
          <span class="fq-status fq-status--${fq.status}">${fq.status} · ${fq.confidence.toFixed(0)}%</span>
        </div>
      `).join('');
    } else {
      flaggedList.innerHTML = '';
    }
  }

  function retakeCurrentSheet() {
    state.results.pop();
    state.sheetsScanned = Math.max(0, state.sheetsScanned - 1);
    openCamera();
  }

  function scanNextSheet() {
    state.capturing = false;
    openCamera();
  }

  // ---------------- summary screen ----------------
  async function finishBatch() {
    if (!state.sessionId) { showView('home'); return; }
    try {
      await fetch(`/api/session/${state.sessionId}/stats`);
    } catch (e) { /* non-critical */ }
    if (state.camera) { state.camera.stop(); state.camera = null; }

    const scanned = state.results.length;
    const avg = scanned ? state.results.reduce((s, r) => s + r.avg_confidence, 0) / scanned : 0;
    const retakes = state.results.filter(r => r.retake_recommended).length;
    $('#summary-grid').innerHTML = `
      <div class="metric"><span class="metric-value">${scanned}</span><span class="metric-label">Sheets Scanned</span></div>
      <div class="metric"><span class="metric-value">${avg.toFixed(0)}%</span><span class="metric-label">Avg Confidence</span></div>
      <div class="metric"><span class="metric-value">${retakes}</span><span class="metric-label">Needed Retake</span></div>
    `;
    $('#summary-tbody').innerHTML = state.results.map((r, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>${r.sheet_label || r.sheet_id}</td>
        <td>${r.avg_confidence.toFixed(0)}%</td>
        <td>${r.flagged_count}</td>
        <td class="${r.retake_recommended ? 'status-flag' : 'status-ok'}">${r.retake_recommended ? 'REVIEW' : 'OK'}</td>
      </tr>
    `).join('');

    showView('summary');
  }

  function startNewSession() {
    state.sessionId = null;
    state.sheetsScanned = 0;
    state.results = [];
    refreshHomeStats();
    showView('home');
  }

  // ---------------- wiring ----------------
  $('#btn-start-scan').addEventListener('click', openCamera);
  $('#btn-close-camera').addEventListener('click', closeCamera);
  $('#btn-retake').addEventListener('click', retakeCurrentSheet);
  $('#btn-next').addEventListener('click', scanNextSheet);
  $('#btn-finish-batch').addEventListener('click', finishBatch);
  $('#btn-new-session').addEventListener('click', startNewSession);

  loadConfig();
})();
