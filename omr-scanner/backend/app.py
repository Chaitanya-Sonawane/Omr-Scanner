"""
app.py
------
Thin HTTP layer around the existing, unmodified OMR backend
(core/align.py, core/template.json, core/scan_omr.py).

This file does NOT change detection logic in any way. It only:
  1. Accepts an already-validated, pre-processed image from the mobile
     capture frontend.
  2. Persists it, calls core.scan_omr.scan_sheet() exactly as the CLI does.
  3. Shapes the existing per-question rows + meta dict the CLI already
     produces into JSON, including confidence scores, so the frontend can
     display them and recommend a retake when appropriate.
  4. Tracks lightweight in-memory batch-session stats for the "scan many
     sheets in a row" exam workflow (no DB required; swap the SessionStore
     for Redis/Postgres in production without touching anything else).

Run:
    pip install -r requirements.txt
    uvicorn app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).parent

# core/ holds the existing OMR pipeline (align.py, scan_omr.py, ...) exactly
# as delivered. Those files import each other as flat top-level modules
# (e.g. scan_omr.py does `from align import ...`), so rather than editing
# them into a package, we put core/ on sys.path and import them the same
# way the original CLI does. Zero lines of pipeline logic are touched.
import sys
sys.path.insert(0, str(BASE_DIR / "core"))
from scan_omr import load_template, scan_sheet, N_QUESTIONS  # noqa: E402
UPLOAD_DIR = BASE_DIR / "uploads"
DEBUG_DIR = BASE_DIR / "debug_overlays"
FRONTEND_DIR = BASE_DIR.parent / "frontend"
UPLOAD_DIR.mkdir(exist_ok=True)
DEBUG_DIR.mkdir(exist_ok=True)

# Below this overall-sheet confidence, the API recommends a retake instead
# of silently accepting the scan. Tunable without touching scan_omr.py.
RETAKE_CONFIDENCE_THRESHOLD = 55.0
# Below this per-question confidence, a question is surfaced to the user
# as "ambiguous" even if the sheet-level average is acceptable.
AMBIGUOUS_QUESTION_THRESHOLD = 50.0

app = FastAPI(title="OMR Scan API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your real origin(s) in production
    allow_methods=["*"],
    allow_headers=["*"],
)

_template = load_template(str(BASE_DIR / "core" / "template.json"))


# --------------------------------------------------------------------------
# In-memory batch session store. A "session" is one exam-hall run: a proctor
# scans many sheets consecutively; the frontend shows a running queue,
# progress, and aggregate stats sourced from here.
# --------------------------------------------------------------------------
class SessionStore:
    def __init__(self):
        self._lock = Lock()
        self._sessions: dict[str, dict] = {}

    def create(self) -> str:
        sid = uuid.uuid4().hex[:12]
        with self._lock:
            self._sessions[sid] = {
                "id": sid,
                "created_at": time.time(),
                "sheets": [],  # list of per-sheet summary dicts
            }
        return sid

    def get(self, sid: str) -> dict:
        with self._lock:
            s = self._sessions.get(sid)
        if s is None:
            raise HTTPException(404, f"Unknown session {sid}")
        return s

    def add_result(self, sid: str, summary: dict):
        with self._lock:
            session = self._sessions.setdefault(
                sid, {"id": sid, "created_at": time.time(), "sheets": []}
            )
            session["sheets"].append(summary)

    def stats(self, sid: str) -> dict:
        session = self.get(sid)
        sheets = session["sheets"]
        n = len(sheets)
        if n == 0:
            return {"session_id": sid, "scanned": 0}
        avg_conf = sum(s["avg_confidence"] for s in sheets) / n
        needs_retake = sum(1 for s in sheets if s["retake_recommended"])
        total_flagged = sum(s["flagged_count"] for s in sheets)
        return {
            "session_id": sid,
            "scanned": n,
            "avg_confidence": round(avg_conf, 1),
            "sheets_needing_retake": needs_retake,
            "total_flagged_questions": total_flagged,
            "sheets": sheets,
        }


sessions = SessionStore()


def _summarize(rows: list[dict], meta: dict) -> dict:
    """Build the confidence-aware summary the frontend needs, purely by
    reading the values scan_sheet() already computes - no re-detection."""
    confidences = [r["Confidence"] for r in rows]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    flagged = [
        {
            "question": r["Question"],
            "status": r["Status"],
            "confidence": r["Confidence"],
            "notes": r["Notes"],
        }
        for r in rows
        if r["Status"] in ("REVIEW", "MULTI") or r["Confidence"] < AMBIGUOUS_QUESTION_THRESHOLD
    ]
    retake_recommended = avg_conf < RETAKE_CONFIDENCE_THRESHOLD or len(flagged) > N_QUESTIONS * 0.25
    return {
        "avg_confidence": round(avg_conf, 1),
        "flagged_count": len(flagged),
        "flagged_questions": flagged,
        "retake_recommended": retake_recommended,
        "sheet_notes": meta.get("sheet_notes", []),
        "align_quality": meta.get("align_quality", {}),
        "image_quality": meta.get("image_quality", {}),
    }


@app.post("/api/session")
def create_session():
    return {"session_id": sessions.create()}


@app.get("/api/session/{session_id}/stats")
def session_stats(session_id: str):
    return sessions.stats(session_id)


@app.post("/api/scan")
async def scan(
    image: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    sheet_label: Optional[str] = Form(None),
):
    """
    Accepts one pre-validated capture from the frontend, runs it through
    the UNMODIFIED align.py -> template.json -> scan_omr.py pipeline, and
    returns per-question results plus confidence-based retake guidance.
    """
    if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, f"Unsupported content type: {image.content_type}")

    sheet_id = uuid.uuid4().hex[:10]
    suffix = Path(image.filename or "sheet.jpg").suffix or ".jpg"
    dest = UPLOAD_DIR / f"{sheet_id}{suffix}"
    data = await image.read()
    if len(data) < 1024:
        raise HTTPException(400, "Uploaded image is empty or too small")
    dest.write_bytes(data)

    try:
        rows, meta = scan_sheet(str(dest), _template, debug_dir=str(DEBUG_DIR))
    except Exception as exc:  # noqa: BLE001 - surface a clean 422, never crash the API
        raise HTTPException(422, f"Could not process sheet: {exc}") from exc

    summary = _summarize(rows, meta)

    result = {
        "sheet_id": sheet_id,
        "sheet_label": sheet_label,
        "questions": rows,
        **summary,
    }

    if session_id:
        sessions.add_result(
            session_id,
            {
                "sheet_id": sheet_id,
                "sheet_label": sheet_label,
                "avg_confidence": summary["avg_confidence"],
                "flagged_count": summary["flagged_count"],
                "retake_recommended": summary["retake_recommended"],
            },
        )

    return JSONResponse(result)


@app.get("/api/health")
def health():
    return {"status": "ok", "questions": N_QUESTIONS}


@app.get("/api/config")
def config():
    """Expose the sheet geometry the frontend needs to judge a preview
    frame (target aspect ratio, canonical size) WITHOUT hardcoding a
    second copy of these numbers that could silently drift from
    core/template.json."""
    return {
        "canon_w": _template["canon_w"],
        "canon_h": _template["canon_h"],
        "target_aspect": _template["canon_w"] / _template["canon_h"],
        "questions": N_QUESTIONS,
        "options_per_question": 4,
    }


# --------------------------------------------------------------------------
# Serve the frontend (camera capture app) as static files from the same
# origin so getUserMedia / ImageCapture work without extra CORS ceremony.
# --------------------------------------------------------------------------
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
