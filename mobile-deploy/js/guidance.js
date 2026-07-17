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
 *   4. A per-check status array for the live validation checklist overlay,
 *      so the user always sees exactly which conditions are passing and
 *      which still need attention — not just the top-priority failure.
 */
const OMRGuidance = (() => {
  const CFG = OMRQuality.CFG;

  const STABILITY_MS = 600;         // continuous "ready" time required before auto-capture (was 900 - felt like it never fired)
  const DRIFT_PX_TOL = 0.05;        // fractional corner drift (of frame diag) allowed during stability hold (was 0.03 - restarted on normal hand tremor)

  /**
   * Evaluate all validation checks against `metrics` and return their
   * individual pass/fail state. This runs independently of the priority
   * ordering used for the single banner message, so ALL checks are always
   * visible in the checklist even when several fail simultaneously.
   *
   * Returns an array of { id, label, pass, hint } objects in display order.
   */
  function evaluateChecks(metrics) {
    const sheetOk = !!metrics.sheetFound;

    // Distance: derived from coverage (areaFrac).
    const coverPct = (metrics.areaFrac * 100).toFixed(0);
    const tooFar   = sheetOk && metrics.areaFrac < CFG.idealAreaFrac[0];
    const tooClose = sheetOk && (metrics.areaFrac > CFG.idealAreaFrac[1] || metrics.clipped);
    const distOk   = sheetOk && !tooFar && !tooClose;
    const distHint = tooFar ? `Move closer (${coverPct}% coverage)` : tooClose ? `Move back (${coverPct}% coverage)` : `${coverPct}% coverage`;

    // Corners detected & not clipped.
    const cornersOk = sheetOk && !metrics.clipped;

    // Template match: aspect ratio + no skew.
    const templateOk = sheetOk
      && (metrics.aspectErr == null || metrics.aspectErr <= CFG.aspectTolerance)
      && !metrics.skewed
      && (metrics.centerOffsetFrac == null || metrics.centerOffsetFrac <= CFG.centerTolFrac);
    const templateHint = !sheetOk ? 'Sheet not found' :
      (metrics.skewed ? 'Straighten the sheet' :
       (metrics.aspectErr > CFG.aspectTolerance ? 'Align to match sheet shape' :
        (metrics.centerOffsetFrac > CFG.centerTolFrac ? 'Center the sheet' : 'Aligned')));

    // Sharpness.
    const sharpOk = sheetOk && metrics.sharpness >= CFG.minSharpness;
    const sharpHint = sharpOk ? `Sharp (${metrics.sharpness ? metrics.sharpness.toFixed(0) : '—'})` : 'Hold steady — image blurry';

    // Lighting (brightness + glare).
    const lightOk = sheetOk
      && metrics.brightness >= CFG.minBrightness
      && metrics.brightness <= CFG.maxBrightness
      && metrics.glareFrac <= CFG.maxGlareFrac;
    const lightHint = !sheetOk ? '' :
      (metrics.brightness < CFG.minBrightness ? 'Too dark — improve lighting' :
       (metrics.brightness > CFG.maxBrightness ? 'Too bright — reduce light' :
        (metrics.glareFrac > CFG.maxGlareFrac ? 'Glare — tilt away from light' : 'Lighting OK')));

    // Stability / motion.
    const steadyOk = metrics.motion <= CFG.maxMotion;
    const steadyHint = steadyOk ? 'Steady' : `Hold still (motion=${metrics.motion ? metrics.motion.toFixed(1) : '—'})`;

    return [
      { id: 'sheet',    label: 'Sheet visible',       pass: sheetOk,    hint: sheetOk ? 'Sheet detected' : 'Point camera at OMR sheet' },
      { id: 'corners',  label: 'Corners detected',    pass: cornersOk,  hint: cornersOk ? 'All 4 corners found' : (sheetOk ? 'Corners clipped — move back' : 'Waiting for sheet') },
      { id: 'template', label: 'Sheet aligned',       pass: templateOk, hint: templateHint },
      { id: 'distance', label: 'Correct distance',    pass: distOk,     hint: distHint },
      { id: 'sharp',    label: 'Sharp focus',         pass: sharpOk,    hint: sharpHint },
      { id: 'light',    label: 'Good lighting',       pass: lightOk,    hint: lightHint },
      { id: 'steady',   label: 'Holding steady',      pass: steadyOk,   hint: steadyHint },
    ];
  }

  // Ordered by priority: first failing check wins the on-screen message.
  function evaluate(metrics) {
    const checks = evaluateChecks(metrics);

    if (!metrics.sheetFound) {
      return { ready: false, state: 'searching', code: 'not_found',
        message: 'Point the camera at the OMR sheet',
        detail: 'Sheet not detected yet', checks };
    }
    if (metrics.motion > CFG.maxMotion) {
      return { ready: false, state: 'warn', code: 'motion',
        message: 'Hold steady',
        detail: `motion=${metrics.motion.toFixed(1)}`, checks };
    }
    if (metrics.areaFrac > CFG.maxAreaFrac || metrics.clipped) {
      return { ready: false, state: 'warn', code: 'too_close',
        message: 'Move back — corners are getting cut off',
        detail: `coverage=${(metrics.areaFrac * 100).toFixed(0)}%`, checks };
    }
    // Gate on the ideal 70-90% coverage band, not just the loose min/max, so
    // auto-capture only fires when the sheet fills the frame as required.
    if (metrics.areaFrac < CFG.idealAreaFrac[0]) {
      return { ready: false, state: 'warn', code: 'too_far',
        message: 'Move closer — fill the frame with the sheet',
        detail: `coverage=${(metrics.areaFrac * 100).toFixed(0)}%`, checks };
    }
    if (metrics.areaFrac > CFG.idealAreaFrac[1]) {
      return { ready: false, state: 'warn', code: 'too_close',
        message: 'Move back slightly — leave a small margin',
        detail: `coverage=${(metrics.areaFrac * 100).toFixed(0)}%`, checks };
    }
    if (metrics.centerOffsetFrac != null && metrics.centerOffsetFrac > CFG.centerTolFrac) {
      return { ready: false, state: 'warn', code: 'off_center',
        message: 'Center the sheet in the frame',
        detail: `offset=${(metrics.centerOffsetFrac * 100).toFixed(0)}%`, checks };
    }
    if (metrics.aspectErr != null && metrics.aspectErr > CFG.aspectTolerance) {
      return { ready: false, state: 'warn', code: 'bad_aspect',
        message: 'This doesn\u2019t match the expected sheet shape — reposition',
        detail: `aspect err=${(metrics.aspectErr * 100).toFixed(0)}%`, checks };
    }
    if (metrics.skewed) {
      return { ready: false, state: 'warn', code: 'skewed',
        message: 'Straighten the sheet — reduce tilt and angle',
        detail: 'corner angles off 90°', checks };
    }
    if (metrics.brightness < CFG.minBrightness) {
      return { ready: false, state: 'warn', code: 'too_dark',
        message: 'Too dark — move to better light',
        detail: `brightness=${metrics.brightness.toFixed(0)}`, checks };
    }
    if (metrics.glareFrac > CFG.maxGlareFrac) {
      return { ready: false, state: 'warn', code: 'glare',
        message: 'Glare detected — tilt away from the light source',
        detail: `glare=${(metrics.glareFrac * 100).toFixed(1)}%`, checks };
    }
    if (metrics.brightness > CFG.maxBrightness) {
      return { ready: false, state: 'warn', code: 'too_bright',
        message: 'Too bright — reduce direct light or flash',
        detail: `brightness=${metrics.brightness.toFixed(0)}`, checks };
    }
    if (metrics.sharpness < CFG.minSharpness) {
      return { ready: false, state: 'warn', code: 'blurry',
        message: 'Image is blurry — hold steady and check focus',
        detail: `sharpness=${metrics.sharpness.toFixed(0)}`, checks };
    }
    return { ready: true, state: 'ready', code: 'ready',
      message: 'Ready — hold still…',
      detail: `coverage=${(metrics.areaFrac * 100).toFixed(0)}% sharp=${metrics.sharpness.toFixed(0)}`,
      checks };
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
        return this.progress;
      }
      const drift = this._quadDrift(this.anchorQuad, metrics.quad, metrics.frameW, metrics.frameH);
      if (drift > DRIFT_PX_TOL) {
        // sheet moved during the hold - restart the clock, don't punish forever
        this.startedAt = now;
        this.anchorQuad = metrics.quad;
        this.progress = 0;
        return this.progress;
      }
      const elapsed = now - this.startedAt;
      this.progress = Math.min(1, elapsed / STABILITY_MS);
      if (this.progress >= 1 && !this.fired) {
        this.fired = true;
        this.onCaptureReady();
      }
      return this.progress;
    }
  }

  return { evaluate, evaluateChecks, StabilityTracker, STABILITY_MS };
})();
