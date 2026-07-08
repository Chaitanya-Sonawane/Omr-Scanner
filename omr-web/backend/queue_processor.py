"""
Sequential background processing queue using omr_scanner.py
"""
import asyncio
import threading
from datetime import datetime
from typing import Any, Dict, List

from omr.omr_scanner import detect_bubbles
from omr.enhancer import enhance_image
import answer_key_store
import results_store
import session as sess_store

_sse_subscribers: Dict[str, List[asyncio.Queue]] = {}
_sse_lock = threading.Lock()
_active_threads: Dict[str, threading.Thread] = {}

OPTION_MAP = {1: "A", 2: "B", 3: "C", 4: "D"}


def subscribe_sse(session_id: str, q: asyncio.Queue):
    with _sse_lock:
        _sse_subscribers.setdefault(session_id, []).append(q)


def unsubscribe_sse(session_id: str, q: asyncio.Queue):
    with _sse_lock:
        subs = _sse_subscribers.get(session_id, [])
        if q in subs:
            subs.remove(q)


def _emit(session_id: str, event: Dict[str, Any]):
    with _sse_lock:
        queues = list(_sse_subscribers.get(session_id, []))
    for q in queues:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass


def _process_sheet(session_id: str, sheet_meta: Dict[str, Any], index: int):
    sheet_id = sheet_meta["sheet_id"]
    filename = sheet_meta["filename"]
    raw_path = sheet_meta["raw_path"]

    _emit(session_id, {"sheet_id": sheet_id, "status": "PROCESSING", "filename": filename})
    sess_store.update_sheet(session_id, sheet_id, {"status": "PROCESSING"})

    detection_payload: Dict[str, Any] = {
        "sheet_id": sheet_id,
        "filename": filename,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "PROCESSING",
    }

    try:
        # 1. Enhance image (Real-ESRGAN if available, else OpenCV CLAHE+sharpen)
        enhanced_path = raw_path.replace("_raw.", "_enhanced.")
        try:
            enhance_image(raw_path, enhanced_path)
            scan_path = enhanced_path
        except Exception as e:
            print(f"[queue] Enhancement failed for {filename}: {e}, scanning raw")
            scan_path = raw_path

        # 2. Scan the OMR sheet
        answers_raw, flags, _ = detect_bubbles(scan_path)
        # 3. Convert to letters
        answers = {q: OPTION_MAP.get(opt, "") if opt is not None else ""
                   for q, opt in answers_raw.items()}

        # 4. Load answer key
        answer_key = answer_key_store.load()  # {q_num(int or str): letter}
        # normalise keys to int
        answer_key = {int(str(k).replace("q", "")): v for k, v in answer_key.items()}

        # 5. Score per question
        per_question = []
        for q in range(1, 41):
            marked  = answers.get(q, "")
            correct = answer_key.get(q, "")
            flag    = flags.get(q)
            # multi_mark is always wrong regardless of correct answer
            is_correct = (flag != "multi_mark") and marked != "" and marked == correct
            per_question.append({
                "q_no": q,
                "marked": marked if flag != "multi_mark" else "MULTI",
                "correct": correct,
                "is_correct": is_correct,
                "flag": flag,
            })

        # 6. Section scores
        section_scores = results_store.compute_sections(per_question)

        # 7. Student id — use pre-filled name if provided, else fallback to Sheet-N
        student_id = sheet_meta.get("student_id") or f"Sheet-{index}"

        # 8. Persist to detection file
        detection_payload.update({
            "status": "DONE",
            "student_id": student_id,
            "total_score": section_scores["total"],
            "out_of": 40,
            "section_scores": section_scores,
            "questions": per_question,
        })
        sess_store.save_detection(session_id, sheet_id, detection_payload)

        # 9. Persist to global results store
        results_store.save_result(
            session_id=session_id,
            student_id=student_id,
            filename=filename,
            per_question=per_question,
            section_scores=section_scores,
        )

        # 10. Update session sheet
        sess_store.update_sheet(session_id, sheet_id, {
            "status": "DONE",
            "student_id": student_id,
            "score": section_scores,
            "detection_file": f"sheets/{sheet_id}_detection.json",
        })

        _emit(session_id, {
            "sheet_id": sheet_id,
            "status": "DONE",
            "filename": filename,
            "student_id": student_id,
            "score": section_scores,
        })

    except Exception as e:
        err_msg = f"Error: {e}"
        detection_payload.update({"status": "ERROR", "error": err_msg})
        sess_store.save_detection(session_id, sheet_id, detection_payload)
        sess_store.update_sheet(session_id, sheet_id, {"status": "ERROR", "error": err_msg})
        _emit(session_id, {"sheet_id": sheet_id, "status": "ERROR", "filename": filename, "error": err_msg})


def _worker(session_id: str, sheets: List[Dict[str, Any]]):
    for index, sheet in enumerate(sheets, start=1):
        _process_sheet(session_id, sheet, index)
    _emit(session_id, {"type": "BATCH_COMPLETE", "session_id": session_id})


def enqueue_sheets(session_id: str, sheets: List[Dict[str, Any]]):
    t = threading.Thread(target=_worker, args=(session_id, sheets), daemon=True)
    _active_threads[session_id] = t
    t.start()
