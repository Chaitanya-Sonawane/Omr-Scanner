/**
 * quality-validation-engine.js
 * ----------------------------
 * The Quality Validation Gate.
 *
 * This replaces the old "capture the instant 4 corners are detected"
 * behaviour with a multi-check gate: capture is only allowed to fire when
 * ALL of the following are simultaneously true for a continuous hold
 * window (HOLD_DURATION_MS):
 *
 *   1. corners      - all 4 sheet corners detected and not clipped
 *   2. coverage     - sheet fills COVERAGE_MIN..100% of the frame
 *   3. perspective  - max corner-angle deviation from 90° <= PERSPECTIVE_MAX_DEG
 *   4. stability    - motion-derived score >= STABILITY_MIN (0..100)
 *   5. sharpness    - normalized Laplacian-variance score >= SHARP_MIN (0..100)
 *   6. lighting     - normalized brightness/glare score >= LIGHT_MIN (0..100)
 *   7. template     - aspect/skew match >= TEMPLATE_MIN (%)
 *
 * The engine is pure logic over the flat metrics object produced by
 * quality.js (OMRQuality.analyzeFrame). It does NOT touch the DOM, the
 * camera, corner detection, perspective correction, or bubble detection -
 * it sits strictly between corner detection (quality.js) and the existing
 * capture call (app.js -> capture.js). Sharpness/lighting are read from
 * metrics that quality.js already computes over the corner-bounded ROI
 * (boundingRectClamped), so no extra full-frame getImageData scan is added
 * here - the per-frame cost of this gate is a handful of arithmetic ops.
 *
 * ---------------------------------------------------------------------------
 * CALIBRATION STATUS: tuned for real handheld use.
 * ---------------------------------------------------------------------------
 * The original constants were reference placeholders (coverage 95-100%,
 * perspective 2 deg, stability/sharp/light 90-95, template 99%) that were
 * effectively unsatisfiable on a real phone: requiring the sheet to fill
 * 95-100% of the frame forces its corners against the frame edge, which
 * trips the `clipped` check and permanently fails `cornersOk`, so `allPass`
 * never became true and auto-capture never fired. The thresholds below are
 * now aligned with the achievable tolerances OMRQuality.CFG uses for the
 * live on-screen guidance, so a well-framed, steady, sharp sheet reliably
 * passes all checks and auto-captures. They can still be re-measured against
 * real device photos, but they are no longer set to values the pipeline can
 * never reach.
 */
const QualityValidationEngine = (() => {

  // Continuous time (ms) all checks must hold true before capture fires.
  // Named constant, not a magic number - see task acceptance criterion #3.
  const HOLD_DURATION_MS = 600;

  // ---- gate thresholds ----
  // Recalibrated to values a handheld phone can actually reach. The previous
  // placeholder values (coverage 0.95-1.0, perspective 2°, stability 95,
  // sharp 90, light 90, template 99%) were self-documented as UNVALIDATED
  // and were effectively unsatisfiable: e.g. requiring the sheet to fill
  // 95-100% of the frame forces its corners against the frame edge, which
  // trips the `clipped` check (edgeMarginFrac) and permanently fails
  // `cornersOk` -> allPass could never become true, so auto-capture never
  // fired even when the sheet looked perfectly aligned. These now mirror the
  // achievable tolerances used by OMRQuality.CFG for live guidance.
  const COVERAGE_MIN      = 0.55;   // sheet must fill >=55% of the frame
  const COVERAGE_MAX      = 0.97;   // leave a small margin so corners aren't clipped
  const PERSPECTIVE_MAX_DEG = 25;   // max corner-angle deviation from 90° (handheld tilt)
  const STABILITY_MIN     = 60;     // 0..100 (motion<=12 on the 480px frame)
  const SHARP_MIN         = 11;     // 0..100 (raw Laplacian variance >= ~22)
  const LIGHT_MIN         = 40;     // 0..100
  const TEMPLATE_MIN      = 78;     // percent (aspect error up to ~0.22)

  // ---- normalization constants (UNVALIDATED placeholders) ----
  // Laplacian-variance floor/ceiling used to scale raw variance -> 0..100.
  // Raw variance here is measured on the ~480px analysis frame inside the
  // corner ROI (quality.js). Placeholder values from the reference engine.
  const SHARP_FLOOR = 0;
  const SHARP_CEIL  = 200;

  // Lighting: brightness mean target/tolerance, plus a glare penalty.
  const MEAN_TARGET    = 150;
  const MEAN_TOLERANCE = 120;
  // glareFrac at/above this contributes a full penalty (drives light score
  // to 0). Reuses the spirit of OMRQuality.CFG.maxGlareFrac.
  const GLARE_FULL_FAIL = 0.06;

  // Stability: motion (mean abs frame-diff from quality.js) mapped to 0..100.
  // motion >= MOTION_FULL_FAIL -> score 0; motion 0 -> score 100. Chosen so
  // that a steady handheld frame (motion ~1) still clears STABILITY_MIN.
  const MOTION_FULL_FAIL = 30;

  // Template: relative aspect-ratio error (from quality.js) mapped to a
  // match percentage. aspectErr 0 -> 100%, aspectErr>=1 -> 0%.
  // Skew (corner angles off 90°) forces a template fail regardless of score.

  function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }

  /** Max deviation (degrees) of the quad's 4 interior angles from 90°. */
  function maxCornerAngleErrorDeg(quad) {
    if (!quad || quad.length !== 4) return 90; // treat missing quad as worst case
    let maxErr = 0;
    for (let i = 0; i < 4; i++) {
      const a = quad[(i + 3) % 4], b = quad[i], c = quad[(i + 1) % 4];
      const v1 = { x: a.x - b.x, y: a.y - b.y };
      const v2 = { x: c.x - b.x, y: c.y - b.y };
      const n1 = Math.hypot(v1.x, v1.y), n2 = Math.hypot(v2.x, v2.y);
      if (n1 < 1e-3 || n2 < 1e-3) return 90;
      const cosA = clamp((v1.x * v2.x + v1.y * v2.y) / (n1 * n2), -1, 1);
      const angDeg = Math.acos(cosA) * 180 / Math.PI;
      const err = Math.abs(angDeg - 90);
      if (err > maxErr) maxErr = err;
    }
    return maxErr;
  }

  // ---- individual score formulas (0..100 unless noted) ----
  function sharpnessScore(rawVariance) {
    if (!(rawVariance > 0)) return 0;
    return clamp(100 * (rawVariance - SHARP_FLOOR) / (SHARP_CEIL - SHARP_FLOOR), 0, 100);
  }
  function lightingScore(brightness, glareFrac) {
    if (!(brightness >= 0)) return 0;
    const meanScore = clamp(100 * (1 - Math.abs(brightness - MEAN_TARGET) / MEAN_TOLERANCE), 0, 100);
    const glarePenalty = clamp((glareFrac || 0) / GLARE_FULL_FAIL, 0, 1);
    return meanScore * (1 - glarePenalty);
  }
  function stabilityScore(motion) {
    const m = motion || 0;
    return clamp(100 * (1 - m / MOTION_FULL_FAIL), 0, 100);
  }
  function templateMatchPct(aspectErr) {
    if (aspectErr == null) return 0;
    return clamp(100 * (1 - aspectErr), 0, 100);
  }

  /**
   * Pure evaluation of all checks for a single frame. Returns the six/seven
   * checks with their pass flags, numeric values, per-check hints, the
   * priority guidance string, and an allPass flag. Stateless - the hold
   * timer lives in the Gate class below.
   */
  function evaluateChecks(metrics) {
    const cornersOk = !!metrics.sheetFound && !metrics.clipped;

    const coveragePct = (metrics.areaFrac || 0) * 100;
    const coverageOk = cornersOk
      && metrics.areaFrac >= COVERAGE_MIN
      && metrics.areaFrac <= COVERAGE_MAX;

    const perspErrDeg = cornersOk ? maxCornerAngleErrorDeg(metrics.quad) : 90;
    const perspectiveOk = cornersOk && perspErrDeg <= PERSPECTIVE_MAX_DEG;

    const stab = stabilityScore(metrics.motion);
    const stabilityOk = cornersOk && stab >= STABILITY_MIN;

    const sharp = sharpnessScore(metrics.sharpness);
    const sharpnessOk = cornersOk && sharp >= SHARP_MIN;

    const light = lightingScore(metrics.brightness, metrics.glareFrac);
    const lightingOk = cornersOk && light >= LIGHT_MIN;

    const tmpl = templateMatchPct(metrics.aspectErr);
    const templateOk = cornersOk && !metrics.skewed && tmpl >= TEMPLATE_MIN;

    // Display order matches the checklist UI; pass flags are independent so
    // every check is always visible even when several fail at once.
    const checks = [
      { id: 'corners',     label: 'Corners detected',  pass: cornersOk,     value: metrics.sheetFound ? (metrics.clipped ? 'clipped' : 'all 4') : 'none' },
      { id: 'coverage',    label: 'Sheet coverage',    pass: coverageOk,    value: `${coveragePct.toFixed(0)}%` },
      { id: 'perspective', label: 'Squared to camera', pass: perspectiveOk, value: `${perspErrDeg.toFixed(1)}°` },
      { id: 'stability',   label: 'Holding steady',    pass: stabilityOk,   value: stab.toFixed(0) },
      { id: 'sharpness',   label: 'Sharp focus',       pass: sharpnessOk,   value: sharp.toFixed(0) },
      { id: 'lighting',    label: 'Good lighting',     pass: lightingOk,    value: light.toFixed(0) },
      { id: 'template',    label: 'Matches template',  pass: templateOk,    value: `${tmpl.toFixed(0)}%` },
    ];

    const allPass = checks.every(c => c.pass);
    return {
      checks, allPass, cornersOk,
      guidance: buildGuidance(metrics, {
        cornersOk, coverageOk, perspectiveOk, stabilityOk, sharpnessOk, lightingOk, templateOk,
        coveragePct, perspErrDeg,
      }),
    };
  }

  /**
   * Single prioritized instruction. Priority order matches the reference
   * _buildGuidance (task criterion #4):
   *   corners -> coverage -> perspective -> stability -> sharpness ->
   *   lighting -> template match. First failing check wins.
   */
  function buildGuidance(metrics, s) {
    if (!s.cornersOk) {
      return metrics.sheetFound
        ? 'Move back — corners are cut off'
        : 'Point the camera at the OMR sheet';
    }
    if (!s.coverageOk) {
      return metrics.areaFrac < COVERAGE_MIN
        ? `Move closer — fill the frame (${s.coveragePct.toFixed(0)}%)`
        : `Move back slightly (${s.coveragePct.toFixed(0)}%)`;
    }
    if (!s.perspectiveOk) return 'Hold the sheet flat and square to the camera';
    if (!s.stabilityOk)   return 'Hold steady';
    if (!s.sharpnessOk)   return 'Image blurry — steady your hand and let it focus';
    if (!s.lightingOk)    return 'Improve lighting — avoid glare and shadows';
    if (!s.templateOk)    return 'Align the sheet to match the template';
    return 'Hold still…';
  }

  /**
   * Stateful gate: call .update(metrics, now) every analyzed frame.
   * Fires onCapture() exactly once when all checks have held true for a
   * continuous HOLD_DURATION_MS. Any single check failing (including corners
   * being lost) resets the hold timer to zero.
   *
   * Returns a per-frame result: { checks, allPass, guidance, holdProgress,
   * shouldCapture }.
   */
  class Gate {
    constructor(onCapture) {
      this.onCapture = onCapture;
      this.reset();
    }
    reset() {
      this.holdStartAt = null;
      this.progress = 0;
      this.fired = false;
    }
    update(metrics, now) {
      const evalResult = evaluateChecks(metrics);

      if (!evalResult.allPass) {
        // Any check failing (corners lost, blur, motion, ...) restarts the
        // hold clock immediately.
        this.holdStartAt = null;
        this.progress = 0;
        return { ...evalResult, holdProgress: 0, shouldCapture: false };
      }

      if (this.holdStartAt === null) {
        this.holdStartAt = now;
      }
      const elapsed = now - this.holdStartAt;
      this.progress = clamp(elapsed / HOLD_DURATION_MS, 0, 1);

      let shouldCapture = false;
      if (this.progress >= 1 && !this.fired) {
        this.fired = true;
        shouldCapture = true;
        if (typeof this.onCapture === 'function') this.onCapture();
      }
      return { ...evalResult, holdProgress: this.progress, shouldCapture };
    }
  }

  return {
    Gate,
    evaluateChecks,
    // exported for tests / calibration tooling
    sharpnessScore, lightingScore, stabilityScore, templateMatchPct, maxCornerAngleErrorDeg,
    HOLD_DURATION_MS,
    THRESHOLDS: {
      COVERAGE_MIN, COVERAGE_MAX, PERSPECTIVE_MAX_DEG, STABILITY_MIN,
      SHARP_MIN, LIGHT_MIN, TEMPLATE_MIN,
      SHARP_FLOOR, SHARP_CEIL, MEAN_TARGET, MEAN_TOLERANCE, GLARE_FULL_FAIL, MOTION_FULL_FAIL,
    },
  };
})();

// Support both browser global (index.html script tag) and CommonJS (node test).
if (typeof module !== 'undefined' && module.exports) {
  module.exports = QualityValidationEngine;
}
