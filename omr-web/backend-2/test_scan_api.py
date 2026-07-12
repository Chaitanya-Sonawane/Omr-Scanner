#!/usr/bin/env python3
"""
Direct scan test — calls the backend API over HTTP to test the 4 sheet images.
Usage: python3 test_scan_api.py
"""
import json
import sys
import os
import requests
from pathlib import Path

API = "http://localhost:8001"

# Images to test — paths relative to workspace root
IMAGES = [
    ("debug_Sample_6_-_Doc_Scan_1.jpg",  "Sheet-1 (Doc Scan 1)"),
    ("debug_Sample_6_-_Doc_Scan_2.jpg",  "Sheet-2 (Doc Scan 2)"),
    ("debug_Sample_4_-_Mobile_Photo_1.jpg", "Sheet-3 (Mobile Photo)"),
    ("debug_adrian1.jpg",                "Sheet-4 (Adrian)"),
]

BASE = Path(__file__).parent.parent.parent  # workspace root


def scan_sheet_via_api(img_path: str, name: str) -> dict:
    """POST a sheet image to the API scan endpoint and return parsed JSON."""
    full = BASE / img_path
    if not full.exists():
        return {"error": f"File not found: {full}"}

    # Create a session
    r = requests.post(f"{API}/api/session")
    r.raise_for_status()
    sid = r.json()["session_id"]

    # Load saved answer key into session
    r = requests.post(f"{API}/api/session/{sid}/answer-key/use-saved")
    if r.status_code != 200:
        return {"error": f"No saved answer key: {r.text}"}

    # Upload sheet
    with open(full, "rb") as f:
        r = requests.post(
            f"{API}/api/session/{sid}/sheets",
            files={"files": (Path(img_path).name, f, "image/jpeg")},
            data={"names": name},
        )
    r.raise_for_status()
    sheet_id = r.json()["sheet_ids"][0]

    # Consume the SSE stream synchronously
    result = None
    with requests.get(f"{API}/api/session/{sid}/progress", stream=True, timeout=60) as resp:
        for line in resp.iter_lines():
            if line and line.startswith(b"data:"):
                data = json.loads(line[5:].strip())
                if data["type"] == "DONE":
                    result = data
                elif data["type"] == "ERROR":
                    return {"error": data.get("error", "unknown")}
                elif data["type"] == "BATCH_COMPLETE":
                    break

    # Get full per-question detail
    det = requests.get(f"{API}/api/session/{sid}/detection/{sheet_id}").json()
    return {"summary": result, "detail": det, "session_id": sid}


def print_result(name: str, res: dict):
    if "error" in res:
        print(f"\n{'='*60}")
        print(f"  {name}  — ERROR: {res['error']}")
        return

    det = res["detail"]
    meta = det.get("omr_meta", {})
    qs   = det.get("questions", [])

    correct = sum(1 for q in qs if q.get("is_correct"))
    multi   = sum(1 for q in qs if q.get("flag") == "multi_mark" or q.get("status") == "MULTI")
    review  = sum(1 for q in qs if q.get("flag") == "review"     or q.get("status") == "REVIEW")
    blank   = sum(1 for q in qs if q.get("status") == "BLANK" or (not q.get("marked") and q.get("status") != "MULTI"))

    print(f"\n{'='*60}")
    print(f"  {det.get('student_id', name)}")
    print(f"  Score : {det['total_score']} / {det['out_of']}")
    print(f"  Multi : {multi}   Review: {review}   Blank: {blank}")
    if meta:
        notes = meta.get("sheet_notes", [])
        print(f"  Quality: threshold={meta.get('threshold',0):.1f}  "
              f"range={meta.get('score_min',0):.1f}–{meta.get('score_max',0):.1f}  "
              f"grid={'✓' if meta.get('grid_matched') else '✗'}  "
              f"border={meta.get('align_quality',{}).get('border_confidence','?')}")
        if notes:
            for n in notes:
                print(f"  ⚠  {n}")

    print(f"\n  {'Q':<4} {'Marked':<8} {'Correct':<9} {'Status':<8} Result")
    print(f"  {'-'*44}")
    for q in qs:
        qno     = q.get("q_no", q.get("q", "?"))
        marked  = q.get("marked", "") or "—"
        correct_ans = q.get("correct", "") or "?"
        status  = q.get("status", "")
        ok      = "✓" if q.get("is_correct") else ("~" if status in ("REVIEW","MULTI") else "✗")
        flag    = f" [{q.get('flag')}]" if q.get("flag") else ""
        print(f"  Q{str(qno):<3} {marked:<8} {correct_ans:<9} {status:<8} {ok}{flag}")


def main():
    print(f"Backend: {API}")
    print(f"Testing {len(IMAGES)} sheet(s)...\n")

    for img_path, name in IMAGES:
        print(f"Scanning {name}...", end=" ", flush=True)
        res = scan_sheet_via_api(img_path, name)
        print("done")
        print_result(name, res)

    print(f"\n{'='*60}")
    print("Scan complete.")


if __name__ == "__main__":
    main()
