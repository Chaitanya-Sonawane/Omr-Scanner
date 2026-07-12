"""
omr_engine.py  (backend-2, files(9) edition)
--------------------------------------------
Thin adapter layer between api_server.py and the production scan pipeline
in scan_omr.py.

scan_image() returns the same dict shape the api_server expects:
    {
        "questions": [
            {"q": int, "option": int|None, "status": str, "confidence": float},
            ...
        ],
        "meta": {
            "threshold": float,
            "score_min": float,
            "score_max": float,
            "align_quality": dict,
            "grid_matched": bool,
            "sheet_notes": list[str],
            "image_quality": dict,
        }
    }

scan_sheet() (from scan_omr.py) is the authoritative pipeline:
  align -> grid_correct -> extract_bubble_features -> per_sheet_threshold
  -> classify_question (per-question relative z-score comparison)
"""

import json
import logging
from pathlib import Path

from scan_omr import scan_sheet, load_template as _load_template

log = logging.getLogger("omr_engine")

TEMPLATE_PATH = Path(__file__).parent / "template.json"


def load_template(path=None) -> dict:
    p = Path(path) if path else TEMPLATE_PATH
    return _load_template(str(p))


def scan_image(image_path: str, template: dict = None) -> dict:
    """
    Scan one OMR sheet using the production pipeline.

    Returns a dict compatible with api_server.py expectations.
    """
    if template is None:
        template = load_template()

    rows, meta = scan_sheet(str(image_path), template)

    questions = [
        {
            "q":          r["Question"],
            "option":     r["Selected_Option"] if r["Selected_Option"] != "" else None,
            "status":     r["Status"],
            "confidence": r["Confidence"],
            "notes":      r.get("Notes", ""),
        }
        for r in rows
    ]

    return {"questions": questions, "meta": meta}
