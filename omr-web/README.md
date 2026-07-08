# OMR Evaluation Web App

## Quick Start

### Backend
```bash
cd omr-web/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd omr-web/frontend
npm install
npm run dev     # runs on http://localhost:3000
```

Open http://localhost:3000

## Usage

1. Upload your **answer key** sheet (the master OMR with correct answers)
2. Upload **student sheets** (up to 50 files)
3. Click **Process Sheets** — watch live progress
4. Download the **PDF report** when done

## Notes

- `pytesseract` is optional; install it + Tesseract for name/roll OCR, otherwise sheets are labelled Sheet-1, Sheet-2, etc.
- Sheets with detection confidence < 60% are flagged for manual review (not auto-scored)
- Raw detection JSON is stored at `data/sessions/<id>/sheets/<id>_detection.json` for re-audit
