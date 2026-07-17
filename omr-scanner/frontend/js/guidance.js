/**
 * guidance.js
 * -----------
 * Converts the numeric metrics from quality.js into:
 *   1. A single prioritized human-readable instruction ("Move closer",
 *      "Hold steady", "Too dark", ...) - never leaves the user guessing.
 *   2. A ready/not-ready verdict.
 *   3. A stability timer: capture only fires after every check has been
 *      satisfied continuously for STABILITY_MS, resetting the instant any
 *      condition regresses or the sheet drifts.
 */
const OMRGuidance = (() => {
  const CFG = OMRQuality.CFG;

  // Auto-capture only fires after every strict check has held continuously
  // for STABILITY_MS AND across at least MIN_READY_FRAMES analyzed frames -
  // both a wall-clock hold and a minimum evidence count, so a single lucky
  // frame can never trigger a capture. Deliberately longer than a typical
  // "document scanner" because accuracy, not speed, is the priority here.
  const STABILITY_MS = 600;         // continuous "ready" time required before auto-capture (was 1200 - felt like it never fired)
  const MIN_READY_FRAMES = 3;       // minimum consecutive ready frames as well (was 6)
  const DRIFT_PX_TOL = 0.05;        // fractional corner drift (of frame diag) allowed during stability hold (was 0.02 - restarted on normal hand tremor)

  // Ordered by priority: first failing check wins the on-screen message.
  // Uses the STRICT `ready*` thresholds so the on-screen "Ready" state and
  // the auto-capture gate agree exactly on what "good enough" means.
  function evaluate(metrics) {
    const q = OMRQuality.qualityScore(metrics);
    const withScore = (v) => Object.assign(v, { score: q.score, subScores: q.sub });

    if (!metrics.sheetFound) {
      return withScore({ ready: false, state: 'searching', code: 'not_found',
        message: 'Point the camera at the OMR sheet',
        detail: 'Sheet not detected yet' });
    }
    if (metrics.motion > CFG.readyMaxMotion) {
      return withScore({ ready: false, state: 'warn', code: 'motion',
        message: 'Hold steady',
        detail: `motion=${metrics.motion.toFixed(1)}` });
    }
    if (metrics.areaFrac < CFG.readyAreaFrac[0]) {
      return withScore({ ready: false, state: 'warn', code: 'too_far',
        message: 'Move closer — sheet is too small in frame',
        detail: `coverage=${(metrics.areaFrac * 100).toFixed(0)}%` });
    }
    if (metrics.areaFrac > CFG.readyAreaFrac[1] || metrics.clipped) {
      return withScore({ ready: false, state: 'warn', code: 'too_close',
        message: 'Move back — corners are getting cut off',
        detail: `coverage=${(metrics.areaFrac * 100).toFixed(0)}%` });
    }
    if (metrics.centerOffsetFrac != null && metrics.centerOffsetFrac > CFG.readyCenterTolFrac) {
      return withScore({ ready: false, state: 'warn', code: 'off_center',
        message: 'Center the sheet in the frame',
        detail: `offset=${(metrics.centerOffsetFrac * 100).toFixed(0)}%` });
    }
    if (metrics.aspectErr != null && metrics.aspectErr > CFG.readyAspectTolerance) {
      return withScore({ ready: false, state: 'warn', code: 'bad_aspect',
        message: 'This doesn\u2019t match the expected sheet shape — reposition',
        detail: `aspect err=${(metrics.aspectErr * 100).toFixed(0)}%` });
    }
    if (metrics.skewed || (metrics.quad && !cornerAnglesWithin(metrics.quad, CFG.readySkewTolDeg))) {
      return withScore({ ready: false, state: 'warn', code: 'skewed',
        message: 'Straighten the sheet — reduce tilt and angle',
        detail: 'corner angles off 90°' });
    }
    if (metrics.brightness < CFG.minBrightness) {
      return withScore({ ready: false, state: 'warn', code: 'too_dark',
        message: 'Too dark — move to better light',
        detail: `brightness=${metrics.brightness.toFixed(0)}` });
    }
    if (metrics.glareFrac > CFG.readyMaxGlareFrac) {
      return withScore({ ready: false, state: 'warn', code: 'glare',
        message: 'Glare detected — tilt away from the light source',
        detail: `glare=${(metrics.glareFrac * 100).toFixed(1)}%` });
    }
    if (metrics.brightness > CFG.maxBrightness) {
      return withScore({ ready: false, state: 'warn', code: 'too_bright',
        message: 'Too bright — reduce direct light or flash',
        detail: `brightness=${metrics.brightness.toFixed(0)}` });
    }
    if (metrics.sharpness < CFG.readyMinSharpness) {
      return withScore({ ready: false, state: 'warn', code: 'blurry',
        message: 'Image is blurry — hold steady and check focus',
        detail: `sharpness=${metrics.sharpness.toFixed(0)}` });
    }
    // Final composite gate: every individual check passed, but the overall
    // quality score must also clear the strict floor before we call it
    // ready - catches a frame that's marginal on several dimensions at
    // once without failing any single hard threshold.
    if (q.score < CFG.readyMinScore) {
      return withScore({ ready: false, state: 'warn', code: 'low_score',
        message: 'Almost there — hold steady for a sharper, straighter frame',
        detail: `quality=${q.score} (need ${CFG.readyMinScore})` });
    }
    return withScore({ ready: true, state: 'ready', code: 'ready',
      message: 'Ready — hold still…',
      detail: `quality=${q.score} sharp=${metrics.sharpness.toFixed(0)}` });
  }

  // Corner-angle squareness check with an explicit tolerance (mirrors
  // quality.js's own check, re-used here for the stricter ready gate).
  function cornerAnglesWithin(q, tolDeg) {
    for (let i = 0; i < 4; i++) {
      const a = q[(i + 3) % 4], b = q[i], c = q[(i + 1) % 4];
      const v1 = { x: a.x - b.x, y: a.y - b.y };
      const v2 = { x: c.x - b.x, y: c.y - b.y };
      const n1 = Math.hypot(v1.x, v1.y), n2 = Math.hypot(v2.x, v2.y);
      if (n1 < 1e-3 || n2 < 1e-3) return false;
      const cosA = Math.min(1, Math.max(-1, (v1.x * v2.x + v1.y * v2.y) / (n1 * n2)));
      const angDeg = Math.acos(cosA) * 180 / Math.PI;
      if (Math.abs(angDeg - 90) > tolDeg) return false;
    }
    return true;
  }

  /** Stateful stability tracker. Call .update(metrics) every analyzed frame. */
  class StabilityTracker {
    constructor(onCaptureReady) {
      this.onCaptureReady = onCaptureReady;
      this.reset();
    }
    reset() {
      this.startedAt = null;
      this.anchorQuad = null;
      this.progress = 0;
      this.fired = false;
      this.readyFrames = 0;
    }
    _quadDrift(q1, q2, w, h) {
      const diag = Math.hypot(w, h);
      let maxDrift = 0;
      for (let i = 0; i < 4; i++) {
        const d = Math.hypot(q1[i].x - q2[i].x, q1[i].y - q2[i].y) / diag;
        if (d > maxDrift) maxDrift = d;
      }
      return maxDrift;
    }
    update(metrics, verdict) {
      const now = performance.now();
      if (!verdict.ready) {
        this.reset();
        return this.progress;
      }
      if (this.startedAt === null) {
        this.startedAt = now;
        this.anchorQuad = metrics.quad;
        this.progress = 0;
        this.readyFrames = 1;
        return this.progress;
      }
      const drift = this._quadDrift(this.anchorQuad, metrics.quad, metrics.frameW, metrics.frameH);
      if (drift > DRIFT_PX_TOL) {
        // sheet moved during the hold - restart the clock, don't punish forever
        this.startedAt = now;
        this.anchorQuad = metrics.quad;
        this.progress = 0;
        this.readyFrames = 1;
        return this.progress;
      }
      this.readyFrames += 1;
      const elapsed = now - this.startedAt;
      // Require BOTH the continuous hold time AND the minimum consecutive
      // ready-frame count - progress is the lesser of the two so the ring
      // reflects whichever requirement is still lagging.
      this.progress = Math.min(1, elapsed / STABILITY_MS, this.readyFrames / MIN_READY_FRAMES);
      if (this.progress >= 1 && !this.fired) {
        this.fired = true;
        this.onCaptureReady();
      }
      return this.progress;
    }
  }

  return { evaluate, StabilityTracker, STABILITY_MS, MIN_READY_FRAMES };
})();
