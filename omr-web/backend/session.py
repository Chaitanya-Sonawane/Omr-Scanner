"""
Session management: create, load, persist sessions to disk.
Each session lives at data/sessions/<session_id>/
"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

DATA_ROOT = Path("data/sessions")


def _session_dir(session_id: str) -> Path:
    return DATA_ROOT / session_id


def _session_file(session_id: str) -> Path:
    return _session_dir(session_id) / "session.json"


def create_session() -> Dict[str, Any]:
    session_id = str(uuid.uuid4())
    d = _session_dir(session_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "sheets").mkdir(exist_ok=True)

    session = {
        "session_id": session_id,
        "created_at": datetime.utcnow().isoformat(),
        "answer_key": None,
        "sheets": [],
    }
    _save(session)
    return session


def load_session(session_id: str) -> Dict[str, Any]:
    f = _session_file(session_id)
    if not f.exists():
        raise FileNotFoundError(f"Session not found: {session_id}")
    with open(f) as fh:
        return json.load(fh)


def _save(session: Dict[str, Any]):
    f = _session_file(session["session_id"])
    with open(f, "w") as fh:
        json.dump(session, fh, indent=2)


def set_answer_key(session_id: str, answer_key: Dict[str, str]):
    s = load_session(session_id)
    s["answer_key"] = answer_key
    _save(s)


def add_sheet(session_id: str, sheet_meta: Dict[str, Any]):
    s = load_session(session_id)
    s["sheets"].append(sheet_meta)
    _save(s)


def update_sheet(session_id: str, sheet_id: str, updates: Dict[str, Any]):
    s = load_session(session_id)
    for sheet in s["sheets"]:
        if sheet["sheet_id"] == sheet_id:
            sheet.update(updates)
            break
    _save(s)


def save_detection(session_id: str, sheet_id: str, detection_data: Dict[str, Any]):
    path = _session_dir(session_id) / "sheets" / f"{sheet_id}_detection.json"
    with open(path, "w") as fh:
        json.dump(detection_data, fh, indent=2)
    return str(path)


def load_detection(session_id: str, sheet_id: str) -> Optional[Dict[str, Any]]:
    path = _session_dir(session_id) / "sheets" / f"{sheet_id}_detection.json"
    if not path.exists():
        return None
    with open(path) as fh:
        return json.load(fh)


def sheet_upload_path(session_id: str, sheet_id: str, filename: str) -> Path:
    ext = Path(filename).suffix
    return _session_dir(session_id) / "sheets" / f"{sheet_id}_raw{ext}"


def report_path(session_id: str) -> Path:
    return _session_dir(session_id) / "report.pdf"
