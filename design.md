# OMR Evaluation Web Application — Design

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (React)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ AnswerKey    │  │ StudentSheet │  │ Results /     │  │
│  │ Upload Zone  │  │ Upload Zone  │  │ Report Page   │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
└─────────┼────────────────┼──────────────────┼───────────┘
          │  REST + SSE    │                  │
┌─────────▼────────────────▼──────────────────▼───────────┐
│                  FastAPI Backend (Python)                 │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Session     │  │  Processing  │  │  Report       │  │
│  │  Manager     │  │  Queue       │  │  Generator    │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                 │                   │          │
│  ┌──────▼─────────────────▼───────────────────▼───────┐  │
│  │              OMR Processing Engine                  │  │
│  │  Preprocessor → BubbleDetector → Scorer → Storage  │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
          │
┌─────────▼──────────────────────────────┐
│   Filesystem  data/sessions/<id>/       │
│   ├── answer_key.json                   │
│   ├── answer_key_raw.<ext>              │
│   ├── sheets/                           │
│   │   ├── 001_raw.<ext>                 │
│   │   ├── 001_detection.json            │
│   │   └── 001_annotated.png             │
│   └── report.pdf                        │
└────────────────────────────────────────┘
```

---

## 2. Directory Structure

```
omr-web/
├── backend/
│   ├── main.py                  # FastAPI app, routes
│   ├── session.py               # Session CRUD, disk layout
│   ├── queue_processor.py       # Sequential background processing
│   ├── omr/
│   │   ├── preprocessor.py      # Deskew, crop, threshold
│   │   ├── bubble_detector.py   # Grid mapping, intensity, thresholding
│   │   ├── scorer.py            # Deterministic rule-based scoring
│   │   ├── ocr.py               # Tesseract wrapper + fallback
│   │   └── report.py            # ReportLab PDF builder
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── AnswerKeyZone.jsx
│   │   │   ├── SheetUploadZone.jsx
│   │   │   ├── QueuePanel.jsx
│   │   │   └── ResultsView.jsx
│   │   └── api.js               # Axios wrappers + SSE hook
│   ├── package.json
│   └── vite.config.js
├── requirements.md
└── design.md
```

---

## 3. Data Models

### Session
```json
{
  "session_id": "uuid4",
  "created_at": "ISO8601",
  "answer_key": {
    "q1": "A", "q2": "C", "..": ".."
  },
  "sheets": [
    {
      "sheet_id": "001",
      "filename": "student1.jpg",
      "status": "DONE | PROCESSING | QUEUED | ERROR | FLAGGED",
      "student_id": "Roll-42 | Sheet-1",
      "score": { "total": 32, "intelligence": 8, "science": 9, "social": 7, "math": 8 },
      "detection_file": "sheets/001_detection.json"
    }
  ]
}
```

### Raw Detection JSON (per sheet)
```json
{
  "sheet_id": "001",
  "filename": "student1.jpg",
  "timestamp": "ISO8601",
  "status": "DONE",
  "confidence": 0.87,
  "flagged_for_review": false,
  "global_threshold": 142.5,
  "ocr": { "raw": "John Doe Roll 42", "student_id": "John Doe", "confidence": 0.91 },
  "questions": [
    {
      "q_no": 1,
      "bubble_intensities": { "A": 210, "B": 45, "C": 198, "D": 205 },
      "local_threshold": 127.5,
      "detected_answer": "B",
      "is_blank": false,
      "is_multi_marked": false,
      "confidence": 0.92
    }
  ]
}
```

---

## 4. OMR Processing Engine

### 4.1 Preprocessor (`omr/preprocessor.py`)

```
load_image(path)
  → grayscale
  → gaussian_blur(5×5)
  → find_page_contour()          # Canny + findContours + largest quad
      if failed → raise ProcessingError("page not found")
  → four_point_perspective_warp()
  → resize(TARGET_W=800, TARGET_H=1040)
  → adaptive_threshold()         # for display/debug only; detection uses raw intensities
  → return normalized_image
```

Page contour detection reuses the same Canny + quad-validation approach from the existing `CropPage` processor.

### 4.2 Bubble Grid (`omr/bubble_detector.py`)

The sheet after preprocessing is always 800×1040 px. The 40-question grid is defined as fixed relative coordinates:

```
LEFT COLUMN  (Q1–Q20):   x_start=80,  bubble_w=30, options_gap=45, row_start=180, row_gap=38
RIGHT COLUMN (Q21–Q40):  x_start=430, bubble_w=30, options_gap=45, row_start=180, row_gap=38
Options A/B/C/D at x offsets: [0, 45, 90, 135]
```

These are calibrated for the target sheet design. Can be overridden via `config.json`.

**Detection algorithm:**
```
for each question q in 1..40:
    strip_intensities = []
    for each option o in [A,B,C,D]:
        roi = image[y:y+bh, x:x+bw]
        intensity = mean(roi)          # lower = darker = more filled
        strip_intensities.append(intensity)

    local_thr = compute_local_threshold(strip_intensities, global_thr)
    filled = [o for o,v in zip(options, strip_intensities) if v < local_thr]

    if len(filled) == 0:   answer = ""      # blank
    elif len(filled) > 1:  answer = "MULTI"  # multi-marked
    else:                   answer = filled[0]

    confidence = compute_confidence(strip_intensities, local_thr)
```

**Global threshold** = midpoint of largest intensity gap across all 160 bubble values (same "first large gap" algorithm from `src/core.py`).

**Local threshold** per strip = largest gap in that strip's 4 values; falls back to global if gap < MIN_JUMP.

**Confidence per question** = (second_lowest_intensity - lowest_intensity) / 255  
→ high when one bubble is clearly much darker than the rest.

**Sheet confidence** = mean of all 40 question confidences.  
If sheet_confidence < CONFIDENCE_THRESHOLD (default 0.60) → flag for manual review.

### 4.3 Scorer (`omr/scorer.py`)

Pure function, no side effects:

```python
def score_sheet(detected: dict, answer_key: dict) -> ScoreResult:
    results = {}
    for q in range(1, 41):
        key = f"q{q}"
        detected_ans = detected[key]   # "", "MULTI", or "A"/"B"/"C"/"D"
        correct_ans  = answer_key[key]
        if detected_ans == correct_ans:
            results[key] = {"correct": True, "points": 1}
        else:
            results[key] = {"correct": False, "points": 0}

    sections = {
        "intelligence": sum(results[f"q{q}"]["points"] for q in range(1,11)),
        "science":      sum(results[f"q{q}"]["points"] for q in range(11,21)),
        "social":       sum(results[f"q{q}"]["points"] for q in range(21,31)),
        "math":         sum(results[f"q{q}"]["points"] for q in range(31,41)),
    }
    sections["total"] = sum(sections.values())
    return ScoreResult(per_question=results, sections=sections)
```

No approximation, no rounding, no ML — pure dictionary lookup.

### 4.4 OCR (`omr/ocr.py`)

```
crop header region (top 15% of preprocessed image)
→ pytesseract.image_to_data(PSM_SINGLE_LINE)
→ parse roll number pattern: r'\b\d{2,10}\b'
→ parse name: longest non-numeric token sequence
→ if confidence < 60 or no text found → return fallback_id = f"Sheet-{index}"
```

### 4.5 Report Generator (`omr/report.py`)

Uses ReportLab `SimpleDocTemplate`. Structure:
- **Cover page**: session info, total sheets processed, answer key table
- **Per-student page**: name/ID, status badge, 40-row question table, section scores
- **Summary page**: ranked table of all students

---

## 5. Backend API Design

### Session lifecycle
```
POST /api/session
  → creates UUID session_id, initializes disk structure
  → returns { session_id }

POST /api/session/:id/answer-key   (multipart file)
  → runs preprocessor + bubble_detector on the key sheet
  → stores answer_key.json
  → returns { answers: {q1:"A", ...} }

POST /api/session/:id/sheets       (multipart, multiple files)
  → saves raw files to disk
  → enqueues all sheets into in-memory queue
  → returns { enqueued: N, sheet_ids: [...] }

GET /api/session/:id/progress      (SSE stream)
  → streams { sheet_id, status, progress_pct } events as processing advances
  → client closes connection when all sheets reach terminal state

GET /api/session/:id/results
  → returns full results JSON (all sheets, scores, flags)

GET /api/session/:id/report
  → generates (or returns cached) PDF
  → Content-Disposition: attachment; filename="report.pdf"

GET /api/session/:id/sheet/:sid/raw
  → returns raw detection JSON for audit
```

### Processing Queue
- Single background thread per session using `asyncio` + `concurrent.futures.ThreadPoolExecutor`
- Each sheet goes through: `preprocess → detect → ocr → score → persist`
- On any exception: sheet status = ERROR, error message stored, queue continues with next sheet
- SSE events emitted after each sheet completes

---

## 6. Frontend Design

### Pages / Views
```
App
├── SessionPage          ← auto-created on first load, session_id in URL
│   ├── AnswerKeyZone    ← drag-drop single file, shows parsed key table on success
│   ├── SheetUploadZone  ← drag-drop up to 50 files, shows file list
│   ├── [Process Button] ← triggers POST /sheets + opens SSE listener
│   ├── QueuePanel       ← live list: filename | status badge | confidence
│   └── ResultsView      ← shown after all processing done
│       ├── SummaryTable ← all students ranked
│       └── [Download PDF button]
```

### State machine (per sheet in UI)
```
QUEUED → PROCESSING → DONE
                    → FLAGGED  (amber badge, manual review note)
                    → ERROR    (red badge, error message)
```

### Key UX decisions
- AnswerKeyZone is disabled until a valid answer key is processed
- SheetUploadZone + Process button disabled until answer key is ready
- Each sheet in QueuePanel shows a progress spinner while PROCESSING, then a confidence bar when DONE
- Flagged sheets show a warning icon and are excluded from the auto-scored summary with a note

---

## 7. Confidence Threshold Calibration

| Sheet Quality | Expected Confidence |
|---|---|
| Clean scanner scan | 0.85–0.99 |
| Phone photo, good light | 0.70–0.90 |
| Phone photo, poor light | 0.50–0.75 |
| Heavily creased / xeroxed | 0.40–0.65 |

Default `CONFIDENCE_THRESHOLD = 0.60`. This means a sheet is only auto-scored when the system is reasonably certain about all bubbles. Below this it surfaces for human review — never silently wrong-scored.

---

## 8. Key Design Decisions & Rationale

| Decision | Rationale |
|---|---|
| Python backend (FastAPI) | Leverages existing OpenCV/NumPy ecosystem in this repo |
| SSE instead of WebSocket | Simpler, unidirectional progress stream; no need for bidirectional communication |
| Sequential queue (not parallel) | Avoids CPU thrashing; OpenCV ops are memory-intensive; predictable order |
| Fixed coordinate grid | After perspective correction to fixed dimensions, bubble positions are deterministic |
| Raw detection JSON stored separately | Decouples scanning from scoring; enables re-audit, manual override, future ML training |
| ReportLab for PDF | Pure Python, no headless browser dependency, works in server environment |
| pytesseract with fallback | OCR is best-effort only — system never blocks on OCR failure |
| Confidence flag instead of error | Preserves the sheet data while signaling uncertainty; human can resolve |
