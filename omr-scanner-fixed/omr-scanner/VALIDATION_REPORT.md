# OMR Scanner — Engineering Audit & Validation Report

**Scope reviewed:** `frontend/` (camera capture, live guidance, quality gating)
and `backend/` (`app.py`, `core/align.py`, `core/calibrate_template.py`,
`core/scan_omr.py`, `core/grade.py`, `core/template.json`).

**How this report is organized:** findings are graded by how they were
verified, because that distinction matters more than usual here.

- **Verified by execution** — I generated synthetic OMR sheets, photographed
  them syntactically (perspective warp, rotation, blur, low light,
  overexposure, JPEG recompression, noise, vignette), ran them through the
  *actual* `scan_sheet()` pipeline and the *actual* running FastAPI server,
  and checked results against known ground truth.
- **Verified by static review** — read and reasoned through the code; no
  execution environment existed to test it (this applies to essentially
  everything camera/browser-related).
- **Not verifiable here** — flagged explicitly. This sandbox has no camera,
  no browser runtime, and no real phones. Claims about live-device
  behavior, frame rates, memory over hours of real use, and cross-browser
  quirks are informed code review, not measurement.

---

## 1. Headline finding: a real, reproducible false-answer bug (fixed)

This is the most important thing in this report, so it goes first.

**Symptom:** on a synthetic sheet with 18 genuinely blank questions, the
*unmodified* backend classified **all 18** as answered (`OK` or `MULTI`)
instead of `BLANK` — a 0% blank-detection rate in that run, and a sheet
accuracy of 55% instead of 100%. This wasn't a one-off — it reproduced
identically across 10 different simulated photo conditions (lighting,
blur, compression, noise, perspective).

**Root cause (confirmed by direct feature inspection, not guessed):**
`classify_question()` in `scan_omr.py` picks a "winning" option per
question by z-scoring 4 darkness-related features across that question's 4
bubbles (median/MAD over just **4 samples**). On a genuinely blank
question, all 4 bubbles are just printed outline circles with no ink —
but ordinary JPEG/print/perspective-resample noise still makes them a few
intensity units different from each other. With only 4 samples, that tiny
noise is enough to look statistically significant to the z-score, and the
code had no absolute-scale check to catch it — I confirmed the "winning"
bubble in every false case had `local_bg_contrast` **strongly negative**
(its interior was *lighter* than the paper right outside it — physically
impossible for real ink) and `connected_frac` / `fill_ratio_local` of
exactly `0.0` (the pixel-level ink-blob detector found no ink at all).
The z-score comparison was purely reacting to noise between four
identical blank bubbles and calling it an answer.

**Fix (`backend/core/scan_omr.py`, `classify_question`):** added two
absolute-scale physical-evidence gates, applied before/alongside the
existing relative z-score comparison:

1. If **no** option in the question is even darker than its own local
   background (`local_bg_contrast <= 0` for all four), it's confidently
   `BLANK` — no relative comparison can override that, because a real
   mark is definitionally darker than the paper around it.
2. If the z-score winner clears (1) but only marginally, and the
   pixel-level ink detector also found nothing, the question is downgraded
   from a confident `OK` to `REVIEW` (system's best guess kept, but
   flagged for a human glance) rather than silently trusted.

**Validated after the fix:**
- The 18/18 false positives above → **0 remaining**, sheet accuracy 55%
  → **100%**.
- Re-ran the full 10-scenario battery (below) — **zero regressions**,
  and 8 of 10 scenarios went from 97.5% to **100%** (the 97.5% cases
  turned out to be the *same* underlying bug hitting the sheet's one
  blank question each time).
- Tested against **genuinely faint pencil-level marks** (not just
  dark-pen fills) to make sure the new gates don't over-reject real
  answers: faint marks near the edge of the fix's threshold correctly
  keep their detected answer but get downgraded to `REVIEW` rather than
  either wrongly zeroed out or silently trusted — appropriate, not a
  regression.
- Tested fully-blank and fully-double-marked synthetic sheets (adversarial
  edge cases) — handled correctly (all-blank sheet flags as low-contrast
  `REVIEW`, which is pre-existing, correct, unrelated behavior; all-multi
  sheet correctly reports `MULTI` on all 40).

This is exactly the class of bug the brief was worried about ("even a
single incorrect scan is unacceptable") — it was silent, systematic, and
would have affected real answer sheets with any natural print/lighting
asymmetry between bubbles on a blank row, not just my synthetic data.

---

## 2. Second real bug found by execution: a reproducible 500 crash

**Symptom:** POSTing a garbage/non-sheet image (tested with pure random
noise, and separately confirmed the same failure mode is reachable via any
sheet containing a `MULTI` answer) to `/api/scan` crashed with an
unhandled `500 Internal Server Error` instead of a clean response.

**Root cause (confirmed via traceback):**
```
TypeError: Object of type bool is not JSON serializable
```
`classify_question()` computes some confidence values through `numpy`
(`np.clip`, etc.); those stay `numpy.float64` even after `round()`.
`numpy.float64` happens to subclass Python's `float`, so it serializes
fine — but in `app.py`'s `_summarize()`, `avg_conf < RETAKE_CONFIDENCE_THRESHOLD`
compares a numpy float, and numpy's comparison operators return
`numpy.bool_` — which, unlike `numpy.float64`, is **not** a subclass of
Python's `bool` and is rejected by `json.dumps`. This is pre-existing in
`app.py`, not something introduced by the frontend work, and is
independent of Finding #1.

**Fix (`backend/app.py`):** added `_json_safe()`, a recursive sanitizer
that converts any `numpy.bool_`/`numpy.integer`/`numpy.floating`/
`numpy.ndarray` to native Python types, applied at all three JSON response
boundaries (`/api/scan`, the session-store record, and
`/api/session/{id}/stats`). This fixes it at the correct layer — the
HTTP/JSON boundary — rather than chasing every individual numpy leak
inside `scan_omr.py`'s internals, so it stays correct even if a future
change to the detection code introduces a new numpy-typed value somewhere.

**Validated after the fix:** the exact noise image that produced the 500
now returns `200` with all 40 questions correctly flagged `REVIEW` (as
they should be, since it's not a sheet). Re-tested the `MULTI`-guaranteed
adversarial sheet, all 10 photo-degradation scenarios, and 20 rapid
sequential + 8 concurrent requests through the actual running server —
all `200`, no crashes, no server-log tracebacks.

---

## 3. Backend pipeline: what I verified works well

The existing `align.py`/`calibrate_template.py`/`scan_omr.py` pipeline was
**left structurally untouched** per the brief — only the two bugs above
were fixed. Independent of those bugs, direct execution testing confirms
real strengths worth stating plainly rather than manufacturing problems
that don't exist:

- **Corner/border detection** correctly used `contour_4pt` (its
  highest-confidence method) across every simulated condition, including
  6° rotation + 3% perspective jitter, heavy vignette, gamma shift, and
  70-unit brightness/darkness swings.
- **Grid-line correction** (`grid_correct`) matched successfully
  (`grid_matched: True`) in every non-heavily-blurred scenario, correctly
  cross-checking the border homography against the sheet's own printed
  gridlines.
- **Heavy motion blur** (kernel size 13) was correctly caught by the blur
  gate (`blur_ok: False`, sheet note surfaced) and the pipeline responded
  exactly as designed: every question downgraded to `REVIEW` at reduced
  confidence rather than silently trusting a blurry read. This is the
  intended fail-safe behavior, not a defect — it "failed" my strict
  accuracy scoring only because `REVIEW` isn't `OK`, but the correct
  option was still surfaced under every one of those flagged rows.
- **Confidence propagation end-to-end is correct and complete:**
  `scan_omr.py` → `app.py`'s `_summarize()` → the `/api/scan` JSON →
  `flagged_questions[]` with per-question confidence → frontend
  `renderResult()`. Verified via live HTTP calls, not just code reading.
- **API error handling for malformed input** (empty file, wrong
  content-type, unknown session ID) returns clean `400`/`404`s, not
  crashes.

## 4. Backend: known limitations, not fixed (documented per your instruction not to redesign the pipeline)

- `align.py`'s `auto_orient` (180°-flip detection) is disabled by default
  with a clear docstring explanation that it was found unreliable on this
  form's layout. That's a documented, deliberate trade-off already in the
  code, not something I changed — flagging it here only because a sheet
  fed in truly upside-down will currently warp correctly geometrically but
  read every bubble in the wrong place, with no automatic catch. If
  upside-down submissions are a real risk in your exam-hall workflow,
  this needs either a validated auto-orient heuristic for your specific
  form or a human-visible checkpoint (e.g. show the aligned preview before
  committing).
- `per_sheet_threshold()`'s Otsu/k-means agreement check and
  `MIN_SCORE_RANGE` flat-sheet detection are sheet-level safety nets I did
  not change; they worked correctly in testing (e.g. correctly flagging an
  entirely-blank sheet for review) but are inherently statistical and can
  still be fooled by an unusual sheet (e.g. one where every question is
  genuinely blank *except* one, which will look "flat" globally even
  though that one answer is real — worth knowing if your exams expect a
  high non-response rate on some sections).

---

## 5. Frontend audit — findings and fixes

The camera/quality/guidance frontend (untested territory previously —
there is no execution environment for it here, only static review) had
several real logic gaps. Fixed:

### 5.1 Post-capture "final safety gate" wasn't actually stricter (fixed)
`capture.js`'s `validateFullRes()` downscaled the just-captured
full-resolution photo down to the same tiny 480px analysis width used for
the *live preview loop*, then measured blur (Laplacian variance) on that.
Downscaling smooths an image before the Laplacian ever runs, which
suppresses the very high-frequency signal blur detection depends on — so
this "final, stricter gate before upload" was actually **no more
sensitive to blur than the live preview**, and measured blur at a
resolution nothing like what `align.py`'s own `blur_score()` (which runs
on the full source image) sees. **Fix:** geometry detection still runs on
the small working copy (cheap, doesn't need resolution), but sharpness/
brightness/glare are now measured on a ~1600px crop — in the same
resolution ballpark as the backend's own blur check — with a scale-
compensated threshold so the comparison means the same real-world blur
amount at both gates.

### 5.2 Double-tap could leak a live camera stream (fixed)
`openCamera()` had no re-entrancy guard. A fast double-tap on "Open
Camera" (or tapping Retake while a prior `getUserMedia()` call was still
pending — easy on a slower phone) would start a second `CameraSession`
before the first finished starting; `state.camera` gets overwritten by
the second, and the first stream's tracks are **never stopped** — an
orphaned camera stream keeps the hardware locked on some Android devices
for the rest of the page's life. **Fix:** added a re-entrancy guard plus a
monotonically-increasing `cameraToken` so a session that loses the race
stops itself cleanly instead of leaking.

### 5.3 Closing the camera mid-capture could resurrect the wrong screen (fixed)
`triggerCapture()`'s async chain (`lockForCapture` → flash → grab frame →
validate → upload) had no cancellation check. If the user hit "close
camera" while a capture was in flight, the function kept running in the
background and could still call `showView('processing')` then
`showView('result')` — silently yanking the user from the home screen
they'd already navigated to into a result screen for a capture they never
asked to see land there. **Fix:** every await point now checks the
capture is still associated with the live camera session and bails
cleanly if not. Documented trade-off: if the upload had already reached
the server by the time this fires, the sheet is still recorded server-side
against the session — the local sheet counter and the server's
`/stats` count can then differ by one. That's an intentional "don't lose
data" trade-off over "keep counts perfectly in sync," but worth knowing.

### 5.4 No handling for the camera being taken away mid-session (fixed)
Nothing listened for the camera track's `ended` event. Mobile OSes reclaim
cameras at any time — backgrounding the tab, another app opening the
camera, device sleep, or an Android WebView power-saving kill. Previously
the `<video>` element would just freeze on its last frame while the
analysis loop kept running against that static image — which could
satisfy the stability timer and fire an auto-capture of a stale frame, or
just leave the user staring at a dead preview with no explanation.
**Fix:** the camera track's `ended` event now surfaces a clear "Camera
disconnected" status and stops the analysis loop, rather than failing
silently.

### 5.5 Minor code-correctness fix
`quality.js`'s `boundingRectClamped()` reached for the `window.cv` global
directly instead of using the `cv` parameter every other function in the
file receives — harmless today (they're the same object), but fragile,
and it meant the function couldn't be reused from `capture.js`'s new
higher-resolution sharpness pass without that same global assumption
being valid in the calling context. Fixed to take `cv` explicitly and
exported it from the module.

### 5.6 Architectural risk — not fixed, flagged for a decision
`capture.js` loads OpenCV.js from a hardcoded external CDN
(`docs.opencv.org`) at runtime, with no offline fallback and no
subresource-integrity pin. In an exam-hall context with restricted or
unreliable wifi — a very plausible real deployment environment for an
NMMS-style sheet scanner — this is a single point of failure that takes
down camera guidance entirely, independent of anything else in this
report. Recommend self-hosting `opencv.js` alongside the rest of the
frontend bundle (served from the same FastAPI static mount already used
for everything else) rather than depending on network access to a third
party at scan time. I did not make this change since it's a deployment/
infrastructure decision, not a bug fix, but wanted it stated plainly
rather than buried.

### 5.7 Reviewed and found correct (no change needed)
- Mat/memory lifecycle in `capture.js`'s analysis loop and `quality.js`'s
  detection functions: every `cv.Mat` created per-frame is deleted on
  every code path I traced, including the try/catch error paths.
- The stability-timer / drift-reset logic in `guidance.js`: since the
  analysis loop and its callback run synchronously on the single JS
  thread (via `requestAnimationFrame`), there's no actual race condition
  between an in-flight capture and the next analyzed frame, despite it
  looking like there could be one at first read.
- `retakeCurrentSheet()` / `scanNextSheet()` both correctly reset
  `state.capturing` via their call into `openCamera()`.

---

## 6. What I could not verify (please read this section)

Being direct about this because the brief specifically asked for it:

- **No real camera, browser, or mobile device exists in this environment.**
  Everything in Section 5 is static code review — real, traceable bugs
  with clear fixes, but *not* something I watched fail and then pass on
  an actual phone. Cross-browser behavior (Safari iOS camera constraints,
  older Android Chrome `ImageCapture` support gaps, `getCapabilities()`
  availability for focus/exposure/white-balance locking) could not be
  exercised at all.
- **Frame rate / GPU / battery claims cannot be measured here.** I did not
  claim "smooth 60fps" or specific memory numbers anywhere in this report
  because I have no way to measure them; take the memory-lifecycle review
  in 5.7 as "the code frees what it allocates," not as a measured leak
  test over hours of real use.
- **Backend timing numbers below are from this sandbox's CPU**, not
  representative mobile-network upload times or a production server's
  hardware.

| Scenario | Backend `scan_sheet()` time (this sandbox) |
|---|---|
| Typical single sheet | ~4.0–4.7s |
| Heavy motion blur | ~4.0s (same order — blur doesn't change pipeline cost) |

`scan_sheet()` is CPU-bound (contour search × threshold sweep × gridline
detection × 160 bubble feature extractions); ~4s per sheet on unknown
sandbox hardware is a data point, not a production SLA — benchmark on
your actual server before assuming a batch-scanning throughput number.

---

## 7. Summary of files changed

| File | Change |
|---|---|
| `backend/core/scan_omr.py` | Fixed the blank-vs-answered misclassification bug (Section 1) — two new absolute-evidence guards in `classify_question()`. |
| `backend/app.py` | Fixed the numpy-bool JSON-serialization 500 crash (Section 2) — new `_json_safe()` sanitizer at all response boundaries. |
| `frontend/js/capture.js` | Fixed the post-capture blur-gate resolution bug (5.1); added camera-lost (`ended` event) hook (5.4); added `SHARPNESS_WORK_LONG_EDGE`/`SHARPNESS_SCALE_FACTOR` constants. |
| `frontend/js/app.js` | Fixed double-open camera-stream leak (5.2); fixed stale-navigation-after-close bug (5.3); wired the camera-lost handler. |
| `frontend/js/quality.js` | Fixed `boundingRectClamped` to take `cv` explicitly instead of the `window.cv` global; exported it. |
| `frontend/js/guidance.js` | No changes — reviewed, no defects found. |
| `backend/core/align.py`, `calibrate_template.py`, `grade.py`, `template.json` | No changes — reviewed, no defects found; these were already solidly hardened. |

## 8. Recommendations (not implemented — decisions for you)

1. Self-host `opencv.js` instead of the CDN dependency (5.6) before any
   exam-hall deployment with uncertain network.
2. Decide on an `auto_orient` strategy for upside-down submissions if
   that's a realistic risk for your proctoring workflow.
3. Before trusting this at scale, run it against a batch of **real
   photographed sheets** (not synthetic ones) — synthetic testing found
   and fixed two serious bugs, which is a strong signal the underlying
   architecture is sound, but synthetic sheets cannot fully stand in for
   real pen/pencil ink, real paper texture, and real phone-camera sensor
   noise. I'd treat this report as "materially more trustworthy than
   before, and two real bugs are now fixed," not as "exhaustively proven
   correct on every real-world sheet."
