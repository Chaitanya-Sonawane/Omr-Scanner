"""
Persistent results store - all student results saved across sessions.
Stored at data/all_results.json
"""
import json
from datetime import datetime
from pathlib import Path

_RESULTS_FILE = Path("data/all_results.json")
_RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)

SECTIONS = {
    "intelligence": range(1, 11),   # Q1-10
    "science":      range(11, 21),  # Q11-20
    "social":       range(21, 31),  # Q21-30
    "math":         range(31, 41),  # Q31-40
}


def compute_sections(per_question: list) -> dict:
    """Compute section scores from per-question results."""
    q_map = {q["q_no"]: q["is_correct"] for q in per_question}
    scores = {}
    for section, q_range in SECTIONS.items():
        scores[section] = sum(1 for q in q_range if q_map.get(q, False))
    scores["total"] = sum(scores.values())
    return scores


def save_result(session_id: str, student_id: str, filename: str,
                per_question: list, section_scores: dict):
    """Append a student result to the persistent store."""
    data = _load_all()
    data.append({
        "session_id": session_id,
        "student_id": student_id,
        "filename": filename,
        "timestamp": datetime.utcnow().isoformat(),
        "section_scores": section_scores,
        "per_question": per_question,
    })
    _RESULTS_FILE.write_text(json.dumps(data, indent=2))


def load_all() -> list:
    return _load_all()


def _load_all() -> list:
    if not _RESULTS_FILE.exists():
        return []
    try:
        return json.loads(_RESULTS_FILE.read_text())
    except Exception:
        return []
