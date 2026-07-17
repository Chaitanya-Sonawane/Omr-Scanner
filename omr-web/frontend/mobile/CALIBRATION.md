# Quality Validation Gate — Calibration

Status: **UNVALIDATED (placeholder-derived).**

The gate in `js/quality-validation-engine.js` replaces the old
single-condition auto-capture (fire the instant 4 corners are detected)
with a six/seven-check gate + 600 ms hold timer. Per the task's Calibration
section, the scoring constants were supposed to be derived from **≥15 real
device captures** (sharp / blurry / well-lit / glare / shadow buckets),
logging raw Laplacian variance and raw lighting mean/stddev per bucket.

**Those real captures were not available in this environment.** Per
Calibration point #4, the engine therefore ships with the reference
placeholder constants, and every one of them is flagged here and in the
code as unvalidated. **No threshold was silently loosened** — the strict
task values are used as-is.

## Constants currently in use

| Constant | Value | Meaning | How to re-calibrate |
|---|---|---|---|
| `SHARP_FLOOR` | 60 | raw Laplacian variance → score 0 | 5th–10th percentile of raw variance across the **blurry** bucket |
| `SHARP_CEIL` | 900 | raw Laplacian variance → score 100 | median raw variance across the **sharp** bucket |
| `MEAN_TARGET` | 170 | ideal ROI brightness mean | median mean across the **well-lit** bucket |
| `MEAN_TOLERANCE` | 55 | brightness spread giving score 0 | half the mean-range spanning well-lit → shadow/over-exposed |
| `GLARE_FULL_FAIL` | 0.06 | glare fraction driving lighting → 0 | 90th-percentile glare fraction in the **glare** bucket |
| `MOTION_FULL_FAIL` | 30 | motion (mean abs frame-diff) → stability 0 | motion seen during deliberate hand shake |

Raw variance is measured on the ~480 px analysis frame inside the
corner-bounded ROI (`OMRQuality.analyzeFrame`), so re-calibration must log
values at that same working resolution, not full res.

## Gate thresholds (task acceptance criterion #2, used as stated)

corners present · coverage 95–100 % · sharpness ≥ 90 · lighting ≥ 90 ·
stability ≥ 95 · perspective ≤ 2° · template ≥ 99 %. Hold = 600 ms
(`HOLD_DURATION_MS`).

## Known tensions to resolve with real data (do NOT loosen silently)

1. **Coverage 95–100 % vs. the clipped-corner margin.** `quality.js` flags a
   quad as `clipped` when any corner is within `edgeMarginFrac` (1.5 %) of
   the frame edge, yet a sheet that fills ≥95 % of the frame necessarily
   pushes corners into that margin. The existing detector's realistic
   "ideal" band is `idealAreaFrac = [0.45, 0.90]`. On this project's
   detector, **95 % coverage and un-clipped corners are close to mutually
   exclusive**, so capture may effectively never fire on real hardware.
   Proposed measured replacement once photos exist: `COVERAGE_MIN ≈ 0.85`
   (the current upper "ideal" bound), or relax `edgeMarginFrac`. Flagged,
   not changed.
2. **Template ≥ 99 %** maps to aspect error ≤ 1 %. That is very tight for a
   handheld capture; confirm against real well-aligned sheets before trusting.
3. **Stability ≥ 95** requires motion ≤ ~1.5 at the chosen `MOTION_FULL_FAIL`;
   verify this matches a steady-but-handheld frame on the target device.

## Verification

`js/quality-validation-engine.test.cjs` drives the pure engine through the
acceptance criteria and every "Edge cases" scenario with a simulated clock:

```
node omr-web/frontend/mobile/js/quality-validation-engine.test.cjs
```

All assertions pass (no capture on corners alone, hold-timer reset on a
single check dropping out mid-hold, corner-flicker reset, lens-cover, blank
first frame, overlapping sheets).
