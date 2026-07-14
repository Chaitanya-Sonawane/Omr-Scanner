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
    results: [],           // per-sheet summaries for the batch table
    lastCaptureBlob: null,
    lastSheetLabel: null,
    camera: null,
    stability: null,
    capturing: false,      // guards against double-fire while auto-capture is in flight
    cameraToken: 0,        // bumped on every openCamera()/closeCamera() to detect stale async work
  };

  // ---------------- config ----------------
  async function loadConfig() {
    try {
      // Use the API URL from environment or fallback to relative path
      const apiBase = window.MOBILE_API_URL ? `${window.MOBILE_API_URL}/api/mobile/config` : '/api/mobile/config';
      const res = await fetch(apiBase);
      const cfg = await res.json();
      if (cfg.target_aspect) {
        OMRQuality.setTargetAspect(cfg.target_aspect);
      }
    } catch (e) {
      console.warn('Could not load mobile config, using default aspect ratio', e);
    }
  }

  // ---------------- session/stats ----------------
  async function ensureSession() {
    if (state.sessionId) return state.sessionId;
    const apiBase = window.MOBILE_API_URL ? `${window.MOBILE_API_URL}/api/mobile/session` : '/api/mobile/session';
    const res = await fetch(apiBase, { method: 'POST' });
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

    // The <video> is rendered with `object-fit: cover`, so the preview is
    // scaled to FILL its box and the overflowing axis is cropped equally on
    // both sides. The analysis frame, in contrast, contains the WHOLE video
    // frame (letterbox-free, same aspect as the intrinsic video). Mapping
    // analysis-frame coords directly to a 0..100 viewBox therefore put the
    // outline in the wrong place whenever the preview box aspect differed
    // from the sheet-detection frame aspect (i.e. almost always on a phone in
    // portrait) - the polygon floated off the actual sheet. Reproduce the
    // exact `cover` transform here so the drawn quad lands on the real sheet.
    const video = $('#video');
    const cw = video.clientWidth || fw;
    const ch = video.clientHeight || fh;
    const coverScale = Math.max(cw / fw, ch / fh);
    const dispW = fw * coverScale, dispH = fh * coverScale;
    const offX = (dispW - cw) / 2, offY = (dispH - ch) / 2;
    const toView = (p) => ({
      x: ((p.x * coverScale - offX) / cw) * 100,
      y: ((p.y * coverScale - offY) / ch) * 100,
    });

    const pts = metrics.quad.map(p => { const v = toView(p); return `${v.x},${v.y}`; }).join(' ');
    quadEl.setAttribute('points', pts);
    quadEl.dataset.state = verdict.state === 'ready' ? 'ready' : (verdict.state === 'error' ? 'error' : 'warn');

    cornersEl.innerHTML = metrics.quad.map(p => {
      const { x, y } = toView(p);
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
    const circumference = 119.4; // 2 * PI * r(19)
    const fill = $('#ring-fill');
    fill.style.strokeDashoffset = String(circumference * (1 - progress));
  }

  // ---------------- camera flow ----------------
  // Guards openCamera() against overlapping invocations. Without this, a
  // fast double-tap on "Open Camera" (or Retake immediately followed by
  // another tap while the first getUserMedia() call is still pending -
  // easy to do on a slower phone) starts a SECOND CameraSession before
  // the first has finished starting. state.camera then gets overwritten
  // by the second, and the first stream's tracks are never stopped: an
  // orphaned camera stream keeps running (and keeps the hardware camera
  // locked on some devices) for the rest of the page's life.
  let openingCamera = false;

  async function openCamera() {
    if (openingCamera) return;
    openingCamera = true;
    // Bump a token so any in-flight triggerCapture() from a PREVIOUS
    // camera session can recognize it's stale once this new session
    // takes over (see triggerCapture below).
    const myToken = ++state.cameraToken;
    try {
      showView('camera');
      $('#status-text').textContent = 'Starting camera…';
      $('#status-banner').dataset.state = 'searching';
      $('#batch-count').textContent = state.sheetsScanned;

      try { await ensureSession(); } catch (e) { console.warn('Session init failed, proceeding without session_id:', e); }

      const video = $('#video');
      const analyzeCanvas = $('#canvas-analyze');
      const captureCanvas = $('#canvas-capture');
      const cam = new OMRCapture.CameraSession(video, analyzeCanvas, captureCanvas);

      // Once the live preview is attached, tell the user the vision engine is
      // still loading so a slow OpenCV download doesn't look like a freeze.
      cam.onPreviewReady = () => {
        if (myToken !== state.cameraToken) return;
        $('#status-text').textContent = 'Loading scanner…';
        $('#status-detail').textContent = 'Preparing the vision engine, please hold steady.';
      };

      try {
        await cam.start();
      } catch (e) {
        if (myToken !== state.cameraToken) { cam.stop(); return; }
        $('#status-text').textContent = 'Camera access failed';
        const msg = e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError'
          ? 'Camera permission denied — tap the camera icon in your browser address bar and allow access, then try again.'
          : (e.name === 'NotFoundError'
            ? 'No camera found on this device.'
            : (e.name === 'NotReadableError'
              ? 'The camera is in use by another app — close other camera apps and try again.'
              : (e.message || String(e))));
        $('#status-detail').textContent = msg;
        $('#status-banner').dataset.state = 'error';
        return;
      }

      if (myToken !== state.cameraToken) {
        // Another openCamera()/closeCamera() ran while getUserMedia() was
        // pending - this session lost the race, release it immediately
        // rather than leaving two live streams.
        cam.stop();
        return;
      }

      state.camera = cam;
      state.capturing = false;
      state.stability = new OMRGuidance.StabilityTracker(() => triggerCapture(cam, myToken));

      cam.onStreamEnded = () => {
        if (myToken !== state.cameraToken) return; // already superseded/closed
        state.capturing = false;
        if (state.stability) state.stability.reset();
        $('#status-banner').dataset.state = 'error';
        $('#status-text').textContent = 'Camera disconnected';
        $('#status-detail').textContent = 'The camera stream stopped unexpectedly — close and reopen the camera to continue.';
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

  function closeCamera() {
    state.cameraToken++; // invalidate any in-flight openCamera()/triggerCapture() from this session
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

    // Bails out of the async capture pipeline the instant the camera view
    // is no longer the one this capture started from (user hit "close",
    // or another session took over). Without this check, closing the
    // camera mid-capture didn't actually cancel anything: this function
    // kept awaiting lockForCapture/grabFullResFrame/upload in the
    // background and would eventually call showView('processing') then
    // showView('result') - silently yanking the user from the home
    // screen they'd already navigated back to into a result screen for a
    // capture they never asked to see land there.
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

      // Give the flash/transition a beat, then validate off the main thread's paint.
      await new Promise(r => setTimeout(r, 60));
      if (stale()) return;
      const validation = cam.validateFullRes(canvas);
      await cam.unlockAfterCapture();
      if (stale()) return;

      if (!validation.pass) {
        // Reject locally - never upload a capture we already know is bad.
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
      // Capture completed after the user navigated away from this camera
      // session: drop the result from the LOCAL UI silently rather than
      // surface a screen the user didn't ask for. Known trade-off: the
      // sheet was still scanned and recorded server-side against
      // session_id (see app.py SessionStore) if one was set, so
      // GET /api/session/{id}/stats can end up reporting one more sheet
      // than the local sheetsScanned/results the UI shows. Acceptable for
      // now since it fails toward "not lost" rather than "wrong count",
      // but worth reconciling from server stats if this UI mismatch
      // matters for your workflow.
      if (stale()) return;

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
      sub.textContent = `Confidence ${result.avg_confidence.toFixed(0)}% — below the accuracy threshold`;
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
    // Drop the last (already-uploaded-but-flagged) result from stats and
    // return straight to a live camera so the proctor can rescan.
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
    let stats;
    try {
      const apiBase = window.MOBILE_API_URL ? `${window.MOBILE_API_URL}/api/mobile/session/${state.sessionId}/stats` : `/api/mobile/session/${state.sessionId}/stats`;
      const res = await fetch(apiBase);
      stats = await res.json();
    } catch (e) {
      stats = null;
    }
    if (state.camera) { state.camera.stop(); state.camera = null; }

    const grid = $('#summary-grid');
    const scanned = state.results.length;
    const avg = scanned ? state.results.reduce((s, r) => s + r.avg_confidence, 0) / scanned : 0;
    const retakes = state.results.filter(r => r.retake_recommended).length;
    grid.innerHTML = `
      <div class="metric"><span class="metric-value">${scanned}</span><span class="metric-label">Sheets Scanned</span></div>
      <div class="metric"><span class="metric-value">${avg.toFixed(0)}%</span><span class="metric-label">Avg Confidence</span></div>
      <div class="metric"><span class="metric-value">${retakes}</span><span class="metric-label">Needed Retake</span></div>
    `;
    const tbody = $('#summary-tbody');
    tbody.innerHTML = state.results.map((r, i) => `
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

  // ---------------- auto-start ----------------
  // The product spec requires the camera to come up automatically as soon as
  // the page loads (Adobe Scan / CamScanner style) instead of forcing the
  // user to tap "Open Camera" first. We attempt that here.
  //
  // Cross-browser caveat: Chrome/Edge/Firefox happily call getUserMedia()
  // during page load and simply raise the OS/browser permission prompt.
  // Some engines (notably iOS Safari) require a real user gesture and will
  // reject an unprompted getUserMedia() with NotAllowedError/SecurityError.
  // openCamera() already renders a clear, actionable error banner on the
  // camera view in that case, but a first-load user who never asked for the
  // camera is better served by the home screen and its explicit button, so
  // we detect the "gesture required" rejection and fall back home instead of
  // leaving them staring at an error. A getUserMedia() that succeeds, or that
  // fails for any other reason (no camera, camera busy, permanently denied),
  // keeps the informative camera-view messaging.
  function autoStartCamera() {
    // Only auto-start from the initial/home view and only in a secure context
    // where getUserMedia is available at all (avoids a guaranteed failure on
    // http:// origins where the API is undefined).
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
    if (!views.home.classList.contains('is-active')) return;

    const fallbackHome = () => {
      if (state.cameraToken !== 0) return; // user already interacted; don't override
      if (state.camera) return;            // a stream is live; nothing to fall back from
      showView('home');
      $('#status-banner').dataset.state = 'searching';
    };

    // Probe permission first (where supported) so we only auto-open when it
    // won't surprise the user with a rejection we then have to recover from.
    const attempt = () => openCamera().catch(() => {});
    if (navigator.permissions && navigator.permissions.query) {
      navigator.permissions.query({ name: 'camera' })
        .then((status) => {
          if (status.state === 'denied') { showView('home'); return; }
          attempt();
        })
        .catch(attempt); // permission probe unsupported for 'camera' — just try
    } else {
      attempt();
    }

    // If openCamera surfaced a gesture-required rejection on the camera view,
    // pull the user back to the home screen where the button awaits.
    const banner = $('#status-banner');
    const observer = new MutationObserver(() => {
      if (banner.dataset.state === 'error'
          && /permission denied|allow access/i.test($('#status-detail').textContent || '')
          && !state.camera) {
        fallbackHome();
        observer.disconnect();
      }
    });
    observer.observe(banner, { attributes: true, attributeFilter: ['data-state'] });
    setTimeout(() => observer.disconnect(), 8000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoStartCamera, { once: true });
  } else {
    autoStartCamera();
  }
})();
