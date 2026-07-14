/**
 * capture.js
 * ----------
 * Owns the camera: getUserMedia, the live analysis loop (throttled for
 * mobile battery/CPU), ImageCapture-based focus/exposure/white-balance
 * locking immediately before capture, full-resolution auto-capture once
 * the stability timer in guidance.js fires, a final full-res quality
 * gate, client-side compression, and the upload to /api/scan.
 *
 * OMR bubble detection NEVER happens here - only the same class of
 * geometry/quality checks used for live guidance, re-run once on the
 * full-resolution capture as a final safety gate before upload.
 */
const OMRCapture = (() => {

  const ANALYZE_INTERVAL_MS = 110;      // ~9fps live analysis - enough for smooth guidance, light on CPU
  const ANALYZE_WIDTH = 480;            // downscaled working width for the analysis loop
  const MAX_UPLOAD_LONG_EDGE = 2600;    // only downsize a capture if it's larger than this
  const JPEG_QUALITY_START = 0.92;

  // Post-capture blur re-check needs to run at something close to upload
  // resolution (see validateFullRes) - ANALYZE_WIDTH is far too small to
  // trust as a "final" blur gate. 1600px matches align.py's own
  // DETECT_MAX_DIM working resolution so the two blur measurements are at
  // least in the same ballpark, though they are still not numerically
  // identical (different color conversion path, JPEG re-encode in
  // between) - see README notes on tuning minSharpness if this still
  // over/under-rejects on real devices.
  const SHARPNESS_WORK_LONG_EDGE = 1600;
  // Laplacian variance scales roughly with working resolution; CFG.minSharpness
  // was tuned against ANALYZE_WIDTH (480px). This factor rescales that
  // floor for comparisons made at SHARPNESS_WORK_LONG_EDGE instead, so
  // "too blurry" means the same real-world blur amount at both gates
  // rather than silently becoming stricter or laxer just from the
  // resolution change. Approximate (empirically-reasonable), not a
  // rigorously derived constant - treat as a starting point to re-tune
  // against real captured photos.
  const SHARPNESS_SCALE_FACTOR = (SHARPNESS_WORK_LONG_EDGE / ANALYZE_WIDTH) ** 2;

  let cvReadyPromise = null;
  function loadOpenCV() {
    if (cvReadyPromise) return cvReadyPromise;
    cvReadyPromise = new Promise((resolve, reject) => {
      if (window.cv && window.cv.Mat) { resolve(window.cv); return; }

      // Timeout so a silently-hung OpenCV init doesn't block the camera forever.
      const timeout = setTimeout(() => {
        reject(new Error('OpenCV.js took too long to initialise — check network connectivity'));
      }, 20000);

      const finish = (result) => { clearTimeout(timeout); resolve(result); };
      const fail = (err) => { clearTimeout(timeout); reject(err); };

      const script = document.createElement('script');
      script.src = 'https://docs.opencv.org/4.9.0/opencv.js';
      script.async = true;
      script.onload = () => {
        const check = () => {
          if (window.cv && (window.cv.Mat || window.cv.onRuntimeInitialized)) {
            if (window.cv.Mat) finish(window.cv);
            else window.cv.onRuntimeInitialized = () => finish(window.cv);
          } else setTimeout(check, 30);
        };
        check();
      };
      script.onerror = () => fail(new Error('Failed to load OpenCV.js — check network connectivity'));
      document.head.appendChild(script);
    });
    return cvReadyPromise;
  }

  class CameraSession {
    constructor(videoEl, analyzeCanvas, captureCanvas) {
      this.video = videoEl;
      this.analyzeCanvas = analyzeCanvas;
      this.captureCanvas = captureCanvas;
      this.stream = null;
      this.track = null;
      this.imageCapture = null;
      this.cv = null;
      this.loopHandle = null;
      this.prevGray = null;
      this.stopped = true;
    }

    async start() {
      // Camera first — get the permission prompt up immediately before
      // anything else. Advanced constraints (focusMode) are stripped out
      // because they cause getUserMedia to throw on many browsers/devices
      // that don't advertise support for them as a required constraint.
      const constraints = {
        audio: false,
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 3840 },
          height: { ideal: 2160 },
        },
      };

      // Attempt with high-res first; fall back to a basic constraint set
      // if the device rejects the ideal resolutions (some Android WebViews do).
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia(constraints);
      } catch (e) {
        if (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError') throw e;
        // Retry with minimal constraints
        stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: { facingMode: { ideal: 'environment' } } });
      }

      // Load OpenCV in parallel while the video preview is already running.
      const cv = await loadOpenCV();
      this.cv = cv;
      this.stream = stream;
      this.video.srcObject = this.stream;
      await new Promise(res => {
        if (this.video.readyState >= 2) res();
        else this.video.onloadedmetadata = () => res();
      });
      await this.video.play();

      this.track = this.stream.getVideoTracks()[0];
      if ('ImageCapture' in window) {
        try { this.imageCapture = new ImageCapture(this.track); } catch (e) { this.imageCapture = null; }
      }
      this.stopped = false;

      // Mobile browsers/OSes can reclaim the camera at any time - the tab
      // is backgrounded, another app opens the camera, the device sleeps,
      // or (on some Android WebViews) a long session is silently killed
      // to save power. Without listening for this, the <video> element
      // just freezes on its last frame: the live analysis loop keeps
      // running against a static image, which can eventually satisfy the
      // stability timer and fire an auto-capture of a frame that's
      // actually stale, or just leave the user staring at a dead preview
      // with no indication anything is wrong.
      this.track.addEventListener('ended', () => {
        if (this.stopped) return;
        this.stopped = true;
        if (this.loopHandle) cancelAnimationFrame(this.loopHandle);
        if (typeof this.onStreamEnded === 'function') this.onStreamEnded();
      });
    }

    /**
     * Runs the throttled live-analysis loop. `onFrame(metrics, verdict)` is
     * called once per analyzed frame with the metrics object from
     * quality.js and the guidance verdict from guidance.js.
     */
    runAnalysisLoop(onFrame) {
      const cv = this.cv;
      const canvas = this.analyzeCanvas;
      let lastTs = 0;

      const step = (ts) => {
        if (this.stopped) return;
        this.loopHandle = requestAnimationFrame(step);
        if (ts - lastTs < ANALYZE_INTERVAL_MS) return;
        lastTs = ts;
        if (this.video.videoWidth === 0) return;

        const vw = this.video.videoWidth, vh = this.video.videoHeight;
        const scale = ANALYZE_WIDTH / vw;
        const aw = ANALYZE_WIDTH, ah = Math.round(vh * scale);
        canvas.width = aw; canvas.height = ah;
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        ctx.drawImage(this.video, 0, 0, aw, ah);

        let rgba;
        try {
          rgba = cv.imread(canvas);
        } catch (e) {
          return;
        }
        const gray = new cv.Mat();
        cv.cvtColor(rgba, gray, cv.COLOR_RGBA2GRAY);
        rgba.delete();

        let metrics;
        try {
          metrics = OMRQuality.analyzeFrame(cv, gray, this.prevGray);
        } catch (e) {
          gray.delete();
          return;
        }
        if (this.prevGray) this.prevGray.delete();
        this.prevGray = gray;

        const verdict = OMRGuidance.evaluate(metrics);
        onFrame(metrics, verdict);
      };
      this.loopHandle = requestAnimationFrame(step);
    }

    /** Best-effort lock of focus/exposure/white-balance right before capture. */
    async lockForCapture() {
      if (!this.track || !this.track.getCapabilities) return;
      try {
        const caps = this.track.getCapabilities();
        const advanced = [];
        if (caps.focusMode && caps.focusMode.includes('manual')) {
          advanced.push({ focusMode: 'manual' });
        } else if (caps.focusMode && caps.focusMode.includes('single-shot')) {
          advanced.push({ focusMode: 'single-shot' });
        }
        if (caps.exposureMode && caps.exposureMode.includes('manual')) {
          advanced.push({ exposureMode: 'manual' });
        }
        if (caps.whiteBalanceMode && caps.whiteBalanceMode.includes('manual')) {
          advanced.push({ whiteBalanceMode: 'manual' });
        }
        if (advanced.length) await this.track.applyConstraints({ advanced });
      } catch (e) {
        // Not all browsers/devices expose these controls — capture proceeds regardless.
      }
    }

    async unlockAfterCapture() {
      if (!this.track) return;
      try {
        await this.track.applyConstraints({ advanced: [{ focusMode: 'continuous' }] });
      } catch (e) { /* best effort */ }
    }

    /** Grabs the highest-practical-resolution still frame as an ImageData-backed canvas. */
    async grabFullResFrame() {
      let bitmap = null;
      if (this.imageCapture && this.imageCapture.takePhoto) {
        try {
          const blob = await this.imageCapture.takePhoto();
          bitmap = await createImageBitmap(blob);
        } catch (e) {
          bitmap = null;
        }
      }
      const canvas = this.captureCanvas;
      const ctx = canvas.getContext('2d');
      if (bitmap) {
        canvas.width = bitmap.width; canvas.height = bitmap.height;
        ctx.drawImage(bitmap, 0, 0);
        bitmap.close();
      } else {
        // Fallback: draw directly from the live <video> element at its native resolution.
        canvas.width = this.video.videoWidth;
        canvas.height = this.video.videoHeight;
        ctx.drawImage(this.video, 0, 0, canvas.width, canvas.height);
      }
      return canvas;
    }

    /**
     * Re-runs the same quality checks used for live guidance against the
     * full-resolution capture, as a final gate before anything is
     * uploaded. Returns { pass, verdict, metrics }.
     *
     * IMPORTANT: quad/corner DETECTION still runs on a small working copy
     * (ANALYZE_WIDTH) purely for contour-search speed - that's fine,
     * geometry doesn't need full resolution. But SHARPNESS specifically
     * must NOT be measured on that same tiny copy: downscaling smooths
     * the image before the Laplacian ever runs, which lowers the
     * measured variance for sharp AND blurry photos alike, and - because
     * blur itself removes high-frequency detail that further downscaling
     * would have removed anyway - makes it *harder*, not easier, to tell
     * a sharp photo from a blurry one at 480px than at a resolution close
     * to what the backend actually receives. That undermined this
     * function's one job (catching blur before upload): the old code
     * measured blur at the same coarse resolution as the live preview
     * while calling it "stricter". align.py's own blur_score() runs on
     * the FULL source image, not a downscaled copy - this now measures
     * sharpness on a much larger crop (SHARPNESS_WORK_LONG_EDGE) so it
     * actually tracks what the backend will see.
     */
    validateFullRes(canvas) {
      const cv = this.cv;

      // 1) Geometry pass on a small working copy - cheap, and corner
      // position doesn't need full resolution.
      const geomScale = Math.min(1, ANALYZE_WIDTH / canvas.width);
      const geomWork = document.createElement('canvas');
      geomWork.width = Math.round(canvas.width * geomScale);
      geomWork.height = Math.round(canvas.height * geomScale);
      geomWork.getContext('2d').drawImage(canvas, 0, 0, geomWork.width, geomWork.height);

      const geomRgba = cv.imread(geomWork);
      const geomGray = new cv.Mat();
      cv.cvtColor(geomRgba, geomGray, cv.COLOR_RGBA2GRAY);
      geomRgba.delete();
      const geomMetrics = OMRQuality.analyzeFrame(cv, geomGray, null);
      geomGray.delete();

      // 2) Sharpness/brightness/glare pass on a much larger crop so the
      // Laplacian-variance blur measurement is meaningful at something
      // close to upload resolution, not washed out by an aggressive
      // downscale. Reuses the quad found above (scaled up) so we're
      // still only measuring inside the sheet, not the whole frame.
      const sharpScale = Math.min(1, SHARPNESS_WORK_LONG_EDGE / Math.max(canvas.width, canvas.height));
      const sharpWork = document.createElement('canvas');
      sharpWork.width = Math.round(canvas.width * sharpScale);
      sharpWork.height = Math.round(canvas.height * sharpScale);
      sharpWork.getContext('2d').drawImage(canvas, 0, 0, sharpWork.width, sharpWork.height);

      const sharpRgba = cv.imread(sharpWork);
      const sharpGray = new cv.Mat();
      cv.cvtColor(sharpRgba, sharpGray, cv.COLOR_RGBA2GRAY);
      sharpRgba.delete();

      let sharpROI = null;
      if (geomMetrics.sheetFound && geomMetrics.quad) {
        // geomWork -> sharpWork coordinate scale factor
        const k = sharpScale / geomScale;
        const scaledQuad = geomMetrics.quad.map(p => ({ x: p.x * k, y: p.y * k }));
        sharpROI = OMRQuality.boundingRectClamped(cv, scaledQuad, sharpGray.cols, sharpGray.rows);
      }
      const sharpness = OMRQuality.laplacianVariance(cv, sharpGray, sharpROI);
      const bg = OMRQuality.brightnessAndGlare(cv, sharpGray, sharpROI);
      sharpGray.delete();

      const metrics = { ...geomMetrics, sharpness, brightness: bg.brightness, glareFrac: bg.glareFrac };

      // Stricter than the live-loop gate: this frame gets exactly one
      // chance, so demand a real margin above the live thresholds. Note
      // minSharpness itself is tuned for the ANALYZE_WIDTH scale used
      // live; SHARPNESS_SCALE_FACTOR compensates so this comparison is
      // apples-to-apples against the higher-resolution measurement above.
      const reasons = [];
      if (!metrics.sheetFound) reasons.push('Sheet corners not detected in the captured image');
      if (metrics.sharpness < OMRQuality.CFG.minSharpness * SHARPNESS_SCALE_FACTOR * 1.15) reasons.push('Image is too blurry');
      if (metrics.clipped) reasons.push('Sheet corners are clipped');
      if (metrics.aspectErr != null && metrics.aspectErr > OMRQuality.CFG.aspectTolerance * 1.2) reasons.push('Perspective distortion too high');
      if (metrics.glareFrac > OMRQuality.CFG.maxGlareFrac * 1.3) reasons.push('Glare covers part of the sheet');
      if (metrics.brightness < OMRQuality.CFG.minBrightness * 0.9) reasons.push('Image too dark');
      if (metrics.brightness > OMRQuality.CFG.maxBrightness * 1.05) reasons.push('Image too bright / overexposed');

      return { pass: reasons.length === 0, reasons, metrics };
    }

    stop() {
      this.stopped = true;
      if (this.loopHandle) cancelAnimationFrame(this.loopHandle);
      if (this.prevGray) { this.prevGray.delete(); this.prevGray = null; }
      if (this.stream) this.stream.getTracks().forEach(t => t.stop());
      this.stream = null; this.track = null; this.imageCapture = null;
    }
  }

  /** Compress the full-res canvas to a JPEG blob, only downsizing if it exceeds MAX_UPLOAD_LONG_EDGE. */
  function compressCanvas(canvas) {
    return new Promise((resolve) => {
      const longEdge = Math.max(canvas.width, canvas.height);
      let outCanvas = canvas;
      if (longEdge > MAX_UPLOAD_LONG_EDGE) {
        const s = MAX_UPLOAD_LONG_EDGE / longEdge;
        const c = document.createElement('canvas');
        c.width = Math.round(canvas.width * s);
        c.height = Math.round(canvas.height * s);
        c.getContext('2d').drawImage(canvas, 0, 0, c.width, c.height);
        outCanvas = c;
      }
      const tryQuality = (q) => {
        outCanvas.toBlob((blob) => {
          if (!blob) { resolve(null); return; }
          if (blob.size > 8 * 1024 * 1024 && q > 0.6) {
            tryQuality(q - 0.08);
          } else {
            resolve(blob);
          }
        }, 'image/jpeg', q);
      };
      tryQuality(JPEG_QUALITY_START);
    });
  }

  async function uploadSheet(blob, { sessionId, sheetLabel } = {}) {
    const form = new FormData();
    form.append('image', blob, 'sheet.jpg');
    if (sessionId) form.append('session_id', sessionId);
    if (sheetLabel) form.append('sheet_label', sheetLabel);
    const apiBase = window.MOBILE_API_URL ? `${window.MOBILE_API_URL}/api/mobile/scan` : '/api/mobile/scan';
    const resp = await fetch(apiBase, { method: 'POST', body: form });
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`Upload failed (${resp.status}): ${text}`);
    }
    return resp.json();
  }

  return { CameraSession, compressCanvas, uploadSheet, loadOpenCV };
})();
