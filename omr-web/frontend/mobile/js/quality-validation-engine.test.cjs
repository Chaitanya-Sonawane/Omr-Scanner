/**
 * Node test harness for the Quality Validation Gate.
 * Run with:  node omr-web/frontend/mobile/js/quality-validation-engine.test.js
 *
 * Verifies the task acceptance criteria and edge cases without a browser /
 * camera by feeding synthetic metrics objects (the same shape quality.js
 * produces) into the pure engine and stepping a simulated clock.
 */
// The engine is a plain browser script (global var), and this project's
// frontend package.json marks .js as ESM, so a bare require() would load it
// as an ES module and skip its CommonJS export. Load it in an isolated VM
// context and pull the global out directly - matches how the browser <script>
// tag exposes `QualityValidationEngine`.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const sandbox = { module: { exports: {} }, console };
vm.runInNewContext(
  fs.readFileSync(path.join(__dirname, 'quality-validation-engine.js'), 'utf8'),
  sandbox
);
const QVE = sandbox.module.exports;

let failures = 0;
function assert(cond, msg) {
  if (cond) { console.log('  PASS:', msg); }
  else { console.log('  FAIL:', msg); failures++; }
}

// A perfectly-passing frame: square quad filling ~97% of a 100x100 frame,
// high sharpness, ideal brightness, no glare, no motion, aspect matched.
function goodMetrics() {
  return {
    sheetFound: true,
    clipped: false,
    skewed: false,
    quad: [ { x: 1, y: 1 }, { x: 99, y: 1 }, { x: 99, y: 99 }, { x: 1, y: 99 } ],
    areaFrac: 0.97,
    aspectErr: 0.002,      // 99.8% template match
    frameW: 100, frameH: 100,
    sharpness: 950,        // well above SHARP_CEIL -> score 100
    brightness: 170,       // == MEAN_TARGET -> score 100
    glareFrac: 0.0,
    motion: 0.2,           // essentially steady
  };
}

function drive(gate, metricsFn, { frames, dtMs = 40, startMs = 1000 }) {
  let captured = false;
  let now = startMs;
  const progressTrace = [];
  for (let i = 0; i < frames; i++) {
    const r = gate.update(metricsFn(i, now), now);
    progressTrace.push(r.holdProgress);
    if (r.shouldCapture) captured = true;
    now += dtMs;
  }
  return { captured, progressTrace };
}

console.log('AC#1: corners detected but sharpness failing -> never captures');
{
  const gate = new QVE.Gate();
  const { captured } = drive(gate, () => {
    const m = goodMetrics();
    m.sharpness = 50; // below SHARP_FLOOR -> score 0
    return m;
  }, { frames: 100 }); // 4s of frames, well past 600ms
  assert(!captured, 'no capture when sharpness fails despite corners present');
}

console.log('AC#1b: corners alone (all quality checks failing) -> never captures');
{
  const gate = new QVE.Gate();
  const { captured } = drive(gate, () => {
    const m = goodMetrics();
    m.sharpness = 10; m.motion = 25; m.brightness = 40; m.aspectErr = 0.5;
    return m;
  }, { frames: 100 });
  assert(!captured, 'corner detection alone does not trigger capture');
}

console.log('AC#2/#3: all six hold for 600ms -> captures exactly once');
{
  let fireCount = 0;
  const gate = new QVE.Gate(() => { fireCount++; });
  const { captured, progressTrace } = drive(gate, goodMetrics, { frames: 40, dtMs: 40 });
  assert(captured, 'capture fires once all checks hold continuously for 600ms');
  assert(fireCount === 1, 'onCapture callback fires exactly once');
  // With dt=40ms, 600ms hold => progress reaches 1 around frame 15.
  assert(progressTrace[5] < 1 && progressTrace[20] >= 1, 'hold progress ramps 0->1 over the window');
}

console.log('AC#3: one check toggled false at ~300ms -> timer resets, no early capture');
{
  const gate = new QVE.Gate();
  // dt=40ms; frame 8 ~= 320ms in. Break stability on that single frame.
  let brokenAt = null;
  const { captured, progressTrace } = drive(gate, (i, now) => {
    const m = goodMetrics();
    if (i === 8) { m.motion = 25; brokenAt = now; } // stability fails once
    return m;
  }, { frames: 12, dtMs: 40 }); // total 480ms < 600ms even ignoring reset
  assert(!captured, 'no capture when a check drops out mid-hold');
  assert(progressTrace[8] === 0, 'hold timer resets to zero on the failing frame');
  assert(progressTrace[9] < progressTrace[7], 'timer restarts after the reset');
}

console.log('Edge: coverage <95% -> "Move closer" guidance, no capture');
{
  const gate = new QVE.Gate();
  let lastGuidance = '';
  const { captured } = drive(gate, () => {
    const m = goodMetrics();
    m.areaFrac = 0.60; // too far
    lastGuidance = QVE.evaluateChecks(m).guidance;
    return m;
  }, { frames: 40 });
  assert(!captured, 'no capture when coverage below 95%');
  assert(/closer/i.test(lastGuidance), `guidance asks to move closer (got: "${lastGuidance}")`);
}

console.log('Edge: corner flicker (corners lost every other frame) -> timer keeps resetting');
{
  const gate = new QVE.Gate();
  const { captured } = drive(gate, (i) => {
    if (i % 2 === 1) return { sheetFound: false }; // corners drop out
    return goodMetrics();
  }, { frames: 60 });
  assert(!captured, 'flickering corners never accumulate a full hold');
}

console.log('Edge: covering the lens mid-hold -> immediate stability+lighting fail, no race capture');
{
  const gate = new QVE.Gate();
  const { captured } = drive(gate, (i) => {
    const m = goodMetrics();
    if (i >= 10) { m.brightness = 5; m.motion = 40; } // lens covered then uncovered noise
    return m;
  }, { frames: 20, dtMs: 40 }); // covered before 600ms reached
  assert(!captured, 'covering the lens prevents capture with no race on the next frame');
}

console.log('Edge: tiny/blank first frame (videoWidth not set) -> no throw, all checks fail');
{
  const gate = new QVE.Gate();
  let threw = false;
  let r;
  try {
    r = gate.update({ sheetFound: false }, 1000);       // empty-ish
    gate.update({}, 1040);                                // totally empty
    gate.update({ sheetFound: true, quad: null, areaFrac: 0 }, 1080);
  } catch (e) { threw = true; }
  assert(!threw, 'blank/degenerate metrics do not throw');
  assert(r && r.checks.every(c => !c.pass), 'all checks fail gracefully on blank input');
}

console.log('Edge: two overlapping sheets (bad aspect + low coverage) -> template & coverage fail');
{
  const m = goodMetrics();
  m.aspectErr = 0.4;   // shape wrong -> template fails
  m.areaFrac = 0.5;    // coverage fails
  const checks = QVE.evaluateChecks(m).checks;
  const byId = Object.fromEntries(checks.map(c => [c.id, c.pass]));
  assert(byId.template === false, 'template match fails on overlapping/mismatched sheet');
  assert(byId.coverage === false, 'coverage fails on overlapping/partial sheet');
}

console.log('');
if (failures === 0) { console.log('ALL TESTS PASSED'); process.exit(0); }
else { console.log(`${failures} TEST(S) FAILED`); process.exit(1); }
