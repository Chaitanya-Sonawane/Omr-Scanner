# OMR Evaluation Web Application — Requirements

## 1. Overview

A full-stack web application that processes scanned OMR (Optical Mark Recognition) sheets for a 40-question exam, evaluates them against an uploaded answer key, and generates a consolidated PDF report. The system must be deterministic, reproducible, and never silently produce wrong scores.

---

## 2. Sheet Structure

- 40 questions total, each with 4 options: A, B, C, D
- Layout: 2 columns on the sheet
  - Left column: Q1–Q20
  - Right column: Q21–Q40
- Section mapping:
  | Questions | Section           |
  |-----------|-------------------|
  | Q1–Q10    | Intelligence Test |
  | Q11–Q20   | Science           |
  | Q21–Q30   | Social Science    |
  | Q31–Q40   | Mathematics       |

---

## 3. Functional Requirements

### FR-1: Answer Key Upload
- Upload a single OMR image or PDF containing the correct answers for all 40 questions
- System detects and stores the 40 answers (A/B/C/D) as the authoritative answer key for the current session
- Answer key is stored in JSON format alongside raw detection data for auditability
- Re-uploading the answer key replaces the previous one and invalidates any existing results

### FR-2: Student Sheet Upload
- Bulk upload of up to 50 OMR sheet images or PDFs
- Accepted formats: PNG, JPG, JPEG, PDF
- Sheets are processed sequentially in upload order (queue-based)
- Frontend shows per-sheet progress indicator during batch processing

### FR-3: Image Pre-Processing Pipeline
Each sheet must pass through the following stages before bubble detection:
1. Grayscale conversion
2. Gaussian blur (noise reduction)
3. Adaptive thresholding (handles uneven lighting)
4. Deskew / perspective correction via contour + 4-point transform
5. Alignment marker detection and crop to normalize orientation
6. Resize to fixed processing dimensions

### FR-4: Bubble Detection
- After alignment, a fixed coordinate grid maps to each of the 40 questions × 4 options = 160 bubble positions
- Per bubble: compute mean pixel intensity of the ROI
- Two-tier thresholding:
  - Global threshold: computed from all 160 bubble intensities per sheet (largest gap in sorted values)
  - Local threshold: computed per question strip (4 bubbles), falls back to global if confidence is low
- Detection result per question: exactly which option(s) crossed the threshold as "filled"

### FR-5: Edge Case Handling
| Scenario | Handling |
|---|---|
| No bubble marked | Marked answer = blank, score = 0 |
| Multiple bubbles marked | Marked answer = multi-marked flag, score = 0 |
| Pre-processing fails (page not found) | Sheet flagged as ERROR, not scored |
| Confidence below threshold | Sheet flagged for MANUAL REVIEW, not auto-scored |
| Corrupt/unreadable image | Sheet flagged as ERROR with message |

No sheet may be silently skipped or silently wrong-scored. Every sheet must have an explicit terminal state.

### FR-6: Confidence Scoring
- Per question: confidence = gap between the highest and second-highest bubble intensity within that strip
- Per sheet: overall confidence = mean confidence across all 40 questions
- If sheet confidence < configured threshold (default: 0.60): flag for manual review
- Flagged sheets are stored with raw detection data so they can be reviewed and scored manually in a later step

### FR-7: Answer Matching & Scoring (Deterministic)
- Rule-based only. No probabilistic or ML-based scoring.
- For each question:
  - 1 point if detected answer matches key exactly
  - 0 points if blank, multi-marked, or wrong answer
- Section score = sum of correct answers in that section (max 10 per section)
- Total score = sum of all 40 questions (max 40)
- Scoring is a pure function of (detected_answers, answer_key) — same inputs always yield same output

### FR-8: Student Identification
- OCR attempt on the sheet header region to extract student name and/or roll number
- If OCR fails or returns low-confidence text: fall back to sheet upload index (1-based) as student ID
- Raw OCR output and confidence stored alongside detection results

### FR-9: PDF Report Generation
The server generates a single consolidated PDF containing:

**Per-student page (one page per sheet):**
- Student ID / Name at the top
- Sheet processing status (OK / FLAGGED / ERROR)
- Table: Q.No | Correct Answer | Marked Answer | Result (✓ or ✗)
- Section-wise and total score summary

**Summary page (last page):**
- Table: Student ID/Name | Total (/40) | Intelligence (/10) | Science (/10) | Social Science (/10) | Mathematics (/10)
- Sorted by Total Score descending

### FR-10: Raw Detection Storage
- Per sheet: store a JSON file containing:
  - Sheet filename
  - Processing status
  - Per-question: { question_no, bubble_intensities[4], detected_answer, confidence, is_multi_marked, is_blank }
  - OCR output (raw + cleaned)
  - Threshold values used (global, per-strip)
  - Timestamp
- These records persist independently of the PDF report
- Re-audit is possible by replaying scoring logic over stored raw detection JSON without re-scanning

---

## 4. Non-Functional Requirements

### NFR-1: Reproducibility
Given the same image file and answer key, the system must produce identical scores on every run. No randomness in the detection or scoring pipeline.

### NFR-2: Transparency
The "manual review" flag must surface early and explicitly. A flagged sheet must never contribute to the PDF summary table with an auto-generated score.

### NFR-3: Performance
- Single sheet processing target: < 5 seconds (on CPU, 1080p image)
- Batch of 50 sheets: < 4 minutes sequential

### NFR-4: Data Isolation
- Each upload session gets a unique session ID
- Sessions do not share answer keys or results
- Sessions stored on disk under `data/sessions/<session_id>/`

---

## 5. API Endpoints (REST)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/session` | Create a new session, returns session_id |
| POST | `/api/session/:id/answer-key` | Upload answer key image/PDF |
| GET | `/api/session/:id/answer-key` | Retrieve parsed answer key |
| POST | `/api/session/:id/sheets` | Upload student sheets (multipart, batch) |
| GET | `/api/session/:id/status` | Get overall processing status + per-sheet queue status |
| GET | `/api/session/:id/results` | Get all results (JSON) |
| GET | `/api/session/:id/report` | Download consolidated PDF report |
| GET | `/api/session/:id/sheet/:sheetId/raw` | Get raw detection JSON for one sheet |

---

## 6. Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend | React (Vite), drag-drop multi-file upload, per-sheet progress |
| Backend | Python (FastAPI) |
| Image Processing | OpenCV (cv2), NumPy |
| OCR | pytesseract (with fallback to index ID) |
| PDF Generation | ReportLab |
| Storage | Local filesystem (JSON + image files) |
| Communication | REST + Server-Sent Events (SSE) for live progress |
