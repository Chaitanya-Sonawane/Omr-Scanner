# backend-2 — Template-Based OMR API

Uses the fixed-template approach from `files(2)` instead of per-sheet circle detection.

## How it works

1. **Calibrate once** — POST a clean reference sheet to `/api/calibrate`. This runs
   `calibrate_template.py`, detects the printed gridlines, computes all 160 bubble
   centres, and writes `template.json`. Re-run only if the sheet layout changes.

2. **Scan** — Every subsequent sheet is warped into the canonical 1400×2200 frame
   (perspective correction), then fill-intensity is sampled at the 160 fixed
   coordinates. A per-sheet Otsu threshold classifies each bubble as
   `OK / BLANK / MULTI / REVIEW`. Nothing is silently guessed on a close call.

## Quick start

```bash
cd omr-web/backend-2
pip install -r requirements.txt
uvicorn api_server:app --reload --port 8001
```

Then calibrate:

```bash
curl -X POST http://localhost:8001/api/calibrate \
     -F "file=@/path/to/clean_reference_sheet.jpg"
```

## API surface (same contract as backend-1)

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/health` | Liveness check |
| POST | `/api/calibrate` | Generate template from reference sheet |
| GET  | `/api/template` | Template metadata |
| POST | `/api/session` | New session |
| POST | `/api/session/{id}/answer-key/manual` | Set key manually |
| POST | `/api/session/{id}/answer-key/use-saved` | Use persisted key |
| POST | `/api/session/{id}/sheets` | Upload student sheets |
| GET  | `/api/session/{id}/progress` | SSE processing stream |
| GET  | `/api/session/{id}/results` | JSON results + stats |
| GET  | `/api/session/{id}/detection/{sheet_id}` | Per-question detail |
| GET  | `/api/session/{id}/export/excel` | Download xlsx |
| POST | `/api/answer-key/save-manual` | Persist key globally |
| GET  | `/api/answer-key` | Fetch persisted key |
