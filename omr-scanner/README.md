# OMR Scan — Mobile Capture Front End

A production-grade mobile camera capture layer bolted **in front of** your
existing, unmodified OMR backend. Nothing in `backend/core/` (align.py,
scan_omr.py, calibrate_template.py, grade.py, template.json) was changed —
those files are copied verbatim. This project's only job is to guarantee
that whatever image reaches them is sharp, square, fully framed, and
correctly exposed.

## Architecture

```
frontend/                         mobile web app (no build step, static files)
  index.html                      view shell: home / camera / processing / result / summary
  css/style.css                   design system (dark viewfinder UI)
  js/quality.js                   pure OpenCV.js frame analysis (sheet-quad, blur, glare, motion...)
  js/guidance.js                  metrics -> human message + stability-before-capture state machine
  js/capture.js                   camera lifecycle, focus/exposure lock, full-res capture, upload
  js/app.js                       view routing, HUD rendering, batch workflow

backend/
  app.py                          FastAPI wrapper: /api/scan, /api/session, /api/config
  core/                           UNTOUCHED — align.py, scan_omr.py, calibrate_template.py,
                                   grade.py, template.json, exactly as provided
  requirements.txt
```

The frontend never re-implements bubble detection or perspective warping —
that stays exclusively in `core/scan_omr.py` / `core/align.py`. The camera
page's live analysis uses the *same class* of check (contour-based sheet
detection, aspect ratio, blur, brightness) purely to decide **when to
capture and whether to accept the shot**, then hands the backend a full,
un-warped photo to align and score itself, so there is only ever one source
of truth for OMR geometry.

## Running it

```bash
cd backend
pip install -r requirements.txt --break-system-packages   # or use a venv
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open `https://<your-host>:8000` on a phone. **Camera access requires
HTTPS** (or `localhost`) per browser security policy — put this behind a
reverse proxy with TLS (nginx/Caddy) for real deployment, or use a tool
like `ngrok`/`ssh -R` while testing on a phone against your dev machine.

## How the capture flow works

1. **Live guidance** (`quality.js` + `guidance.js`, ~9 fps on a downscaled
   480px working frame): detects the sheet's outer quadrilateral the same
   way `align.py` does (adaptive-threshold → contour → 4-point approx →
   aspect-ratio scoring, minAreaRect fallback), then checks coverage,
   centering, skew, aspect ratio, sharpness (Laplacian variance),
   brightness, glare, and motion. The single highest-priority failing
   check drives the on-screen message — the user is never left guessing.
2. **Stability gate**: once every check passes, a 900 ms hold timer starts.
   Any regression, or the sheet drifting more than ~3% of the frame
   diagonal, resets it. No tap-to-capture — this both proves the frame is
   genuinely stable and removes the touch-induced shake of manual capture.
3. **Capture**: `track.applyConstraints()` attempts to lock focus,
   exposure, and white balance (feature-detected — falls back silently on
   devices that don't expose manual capabilities), takes the
   highest-practical-resolution still via `ImageCapture.takePhoto()`
   (falling back to a `<video>` frame grab if `ImageCapture` isn't
   available), then unlocks the track afterward.
4. **Final validation**: the *same* quality pipeline reruns once, at full
   resolution, with stricter thresholds. A failure here rejects locally —
   nothing is ever uploaded — and returns straight to the live preview
   with the specific reason shown.
5. **Compress & upload**: only downsizes if the long edge exceeds 2600px
   (bubble/border detail is preserved by default); JPEG quality steps down
   automatically if the file exceeds 8 MB. Uploads to `POST /api/scan`.
6. **Backend**: `app.py` writes the file, calls
   `core.scan_omr.scan_sheet()` unchanged, and shapes the existing
   per-question `Confidence`/`Status` values the CLI already computes into
   a retake recommendation (`RETAKE_CONFIDENCE_THRESHOLD` /
   `AMBIGUOUS_QUESTION_THRESHOLD` in `app.py` — tune freely without
   touching detection logic).
7. **Batch workflow**: `POST /api/session` starts a running session;
   every `/api/scan` call tagged with that `session_id` accumulates in an
   in-memory store (`SessionStore` in `app.py` — swap for Redis/Postgres
   for multi-worker deployments). The result screen auto-offers "Scan Next
   Sheet", returning straight to a live camera, and a "Finish batch" flow
   renders a summary table sourced from `/api/session/{id}/stats`.

## Tuning

All frontend thresholds live in one place: `OMRQuality.CFG` in
`frontend/js/quality.js` (coverage range, aspect tolerance, sharpness
floor, brightness range, glare fraction, motion ceiling). The target
aspect ratio is **not** hardcoded twice — the frontend fetches it from
`GET /api/config`, which reads `core/template.json` directly, so the two
layers can't silently drift apart.

Backend retake/ambiguity thresholds live in `backend/app.py`
(`RETAKE_CONFIDENCE_THRESHOLD`, `AMBIGUOUS_QUESTION_THRESHOLD`) — separate
from, and without touching, `scan_omr.py`'s own confidence math.

## Notes / production hardening still worth doing

- `SessionStore` is in-process memory — fine for a single-worker deploy or
  a demo; move to Redis/Postgres before running multiple uvicorn workers
  or across restarts.
- OpenCV.js is lazy-loaded from the official CDN
  (`docs.opencv.org/4.9.0/opencv.js`) only when the camera opens, per the
  brief. For fully offline/air-gapped exam halls, self-host that file and
  change the URL in `capture.js`.
- CORS is wide open (`allow_origins=["*"]`) for easy local testing — lock
  this to your real origin before production use.
