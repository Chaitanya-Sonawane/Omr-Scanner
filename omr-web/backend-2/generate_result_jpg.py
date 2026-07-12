#!/usr/bin/env python3
"""
Generate a result JPG for each scanned sheet.
- Left side: warped sheet with colored bubble overlays
- Right side: result card showing Q/Answer/Status per question
"""
import sys
sys.path.insert(0, '.')

import cv2
import numpy as np
from pathlib import Path
from omr_engine import load_template, scan_image
from align import align_sheet, load_image
from scan_omr import normalize_illumination, grid_correct

OUT_DIR = Path("scan_results")
OUT_DIR.mkdir(exist_ok=True)

OPT_MAP = {1: "A", 2: "B", 3: "C", 4: "D"}

# Colors BGR
COL_OK_CORRECT  = (34, 197, 94)    # green
COL_OK_WRONG    = (59, 130, 246)   # blue
COL_MULTI       = (0, 0, 220)      # red
COL_REVIEW      = (0, 165, 255)    # orange
COL_BLANK       = (160, 160, 160)  # grey
COL_TEXT        = (30, 30, 30)
COL_WHITE       = (255, 255, 255)
COL_HEADER_BG   = (37, 99, 235)    # dark blue

SHEETS = [
    ("debug_Sample_6_-_Doc_Scan_1.jpg",     "Doc_Scan_1"),
    ("debug_Sample_6_-_Doc_Scan_2.jpg",     "Doc_Scan_2"),
    ("debug_Sample_4_-_Mobile_Photo_1.jpg", "Mobile_Photo"),
    ("debug_adrian1.jpg",                   "Adrian"),
]


def bubble_color(q_item):
    s = q_item["status"]
    if s == "MULTI":   return COL_MULTI
    if s == "REVIEW":  return COL_REVIEW
    if s == "BLANK":   return COL_BLANK
    return COL_OK_CORRECT   # OK — we don't have answer key on this path, mark green


def draw_sheet_overlay(img_path, template, questions) -> np.ndarray:
    """Warp the sheet and draw colored circles on each bubble."""
    img = load_image(img_path)
    warped, _ = align_sheet(img, out_size=(template["canon_w"], template["canon_h"]))
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    correct_xy, _ = grid_correct(gray, template)

    radius = template["radius"]
    overlay = warped.copy()

    # map q->item for fast lookup
    q_map = {item["q"]: item for item in questions}

    for key, c in template["bubbles"].items():
        q_num, opt = map(int, key.split("_"))
        cx, cy = correct_xy(c["x"], c["y"])
        cx, cy = int(round(cx)), int(round(cy))

        item = q_map.get(q_num)
        if item is None:
            continue

        selected = item["option"]
        status   = item["status"]

        if status == "MULTI":
            color = COL_MULTI
            thickness = 3
        elif status == "REVIEW":
            color = COL_REVIEW
            thickness = 2
        elif status == "BLANK":
            color = COL_BLANK
            thickness = 1
        elif selected == opt:
            color = COL_OK_CORRECT
            thickness = -1   # filled
        else:
            color = (200, 200, 200)
            thickness = 1

        cv2.circle(overlay, (cx, cy), radius, color, thickness)
        if selected == opt and status == "OK":
            cv2.putText(overlay, OPT_MAP.get(opt, ""), (cx - 8, cy + 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, COL_WHITE, 1, cv2.LINE_AA)

    # Scale down to fixed height
    target_h = 1100
    scale = target_h / overlay.shape[0]
    overlay = cv2.resize(overlay, (int(overlay.shape[1] * scale), target_h))
    return overlay


def draw_result_card(questions, sheet_name, meta) -> np.ndarray:
    """Draw a result card image (right panel)."""
    CARD_W  = 520
    ROW_H   = 24
    HEADER  = 110
    FOOTER  = 60
    N       = len(questions)
    CARD_H  = HEADER + N * ROW_H + FOOTER

    card = np.full((CARD_H, CARD_W, 3), 245, dtype=np.uint8)

    # Header
    cv2.rectangle(card, (0, 0), (CARD_W, HEADER), COL_HEADER_BG, -1)
    cv2.putText(card, sheet_name, (14, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, COL_WHITE, 2, cv2.LINE_AA)

    # Meta info
    aq = meta.get("align_quality", {})
    border = aq.get("border_confidence", "?")
    grid   = "yes" if meta.get("grid_matched") else "no"
    blur   = aq.get("blur_score", 0)
    rng    = f"{meta.get('score_min',0):.0f}-{meta.get('score_max',0):.0f}"
    cv2.putText(card, f"Border:{border}  Grid:{grid}  Blur:{blur:.0f}  Range:{rng}",
                (14, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.38, COL_WHITE, 1, cv2.LINE_AA)

    notes = meta.get("sheet_notes", [])
    note_txt = notes[0][:65] if notes else "No issues"
    cv2.putText(card, note_txt, (14, 82),
                cv2.FONT_HERSHEY_SIMPLEX, 0.33, (200, 230, 255), 1, cv2.LINE_AA)

    n_ok     = sum(1 for q in questions if q["status"] == "OK")
    n_multi  = sum(1 for q in questions if q["status"] == "MULTI")
    n_review = sum(1 for q in questions if q["status"] == "REVIEW")
    n_blank  = sum(1 for q in questions if q["status"] == "BLANK")
    summary  = f"OK:{n_ok}  MULTI:{n_multi}  REVIEW:{n_review}  BLANK:{n_blank}"
    cv2.putText(card, summary, (14, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 230, 100), 1, cv2.LINE_AA)

    # Column headers
    y0 = HEADER
    cv2.rectangle(card, (0, y0), (CARD_W, y0 + ROW_H), (210, 210, 220), -1)
    for x, lbl in [(10, "Q"), (60, "Answer"), (160, "Status"), (280, "Conf"), (390, "")]:
        cv2.putText(card, lbl, (x, y0 + 17),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, COL_TEXT, 1, cv2.LINE_AA)

    # Rows
    for i, item in enumerate(questions):
        y = HEADER + (i + 1) * ROW_H
        bg = (255, 255, 255) if i % 2 == 0 else (240, 240, 245)
        cv2.rectangle(card, (0, y), (CARD_W, y + ROW_H), bg, -1)

        status = item["status"]
        opt    = OPT_MAP.get(item["option"], "—") if item["option"] else "—"
        conf   = f'{item["confidence"]:.0f}%'

        if status == "MULTI":
            sc = COL_MULTI; opt = "MULTI"
        elif status == "REVIEW":
            sc = (0, 120, 200)
        elif status == "BLANK":
            sc = (120, 120, 120); opt = "—"
        else:
            sc = (30, 140, 30)

        # dot indicator
        dot_color = bubble_color(item)
        cv2.circle(card, (8, y + 14), 6, dot_color, -1)

        cv2.putText(card, f"Q{item['q']}", (18, y + 17),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, COL_TEXT, 1, cv2.LINE_AA)
        cv2.putText(card, opt,  (60,  y + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45, sc,      1, cv2.LINE_AA)
        cv2.putText(card, status,(160, y + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.38, sc,      1, cv2.LINE_AA)
        cv2.putText(card, conf,  (280, y + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.38, COL_TEXT,1, cv2.LINE_AA)

        # bar
        bar_w = int(item["confidence"] / 100.0 * 100)
        cv2.rectangle(card, (380, y + 6), (380 + bar_w, y + 18), dot_color, -1)

    # Footer legend
    yf = HEADER + (N + 1) * ROW_H + 8
    for x, color, label in [
        (10,  COL_OK_CORRECT, "OK"),
        (70,  COL_MULTI,      "MULTI"),
        (150, COL_REVIEW,     "REVIEW"),
        (250, COL_BLANK,      "BLANK"),
    ]:
        cv2.circle(card, (x, yf + 8), 7, color, -1)
        cv2.putText(card, label, (x + 12, yf + 13),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, COL_TEXT, 1, cv2.LINE_AA)

    return card


def combine(sheet_img, card_img) -> np.ndarray:
    """Side-by-side: sheet overlay | result card."""
    sh = sheet_img.shape[0]
    ch = card_img.shape[0]
    # pad shorter one
    if sh > ch:
        pad = np.full((sh - ch, card_img.shape[1], 3), 245, dtype=np.uint8)
        card_img = np.vstack([card_img, pad])
    elif ch > sh:
        pad = np.full((ch - sh, sheet_img.shape[1], 3), 245, dtype=np.uint8)
        sheet_img = np.vstack([sheet_img, pad])
    # divider
    div = np.full((max(sh, ch), 4, 3), 180, dtype=np.uint8)
    return np.hstack([sheet_img, div, card_img])


def main():
    template = load_template()

    for img_path, label in SHEETS:
        p = Path(img_path)
        if not p.exists():
            print(f"SKIP (not found): {img_path}")
            continue

        print(f"Scanning {label}...", end=" ", flush=True)
        try:
            res    = scan_image(img_path, template)
            qs     = res["questions"]
            meta   = res["meta"]

            sheet_overlay = draw_sheet_overlay(img_path, template, qs)
            card          = draw_result_card(qs, label.replace("_", " "), meta)
            combined      = combine(sheet_overlay, card)

            out = OUT_DIR / f"result_{label}.jpg"
            cv2.imwrite(str(out), combined, [cv2.IMWRITE_JPEG_QUALITY, 92])
            n_ok     = sum(1 for q in qs if q["status"] == "OK")
            n_multi  = sum(1 for q in qs if q["status"] == "MULTI")
            n_review = sum(1 for q in qs if q["status"] == "REVIEW")
            n_blank  = sum(1 for q in qs if q["status"] == "BLANK")
            print(f"done → {out}  [OK:{n_ok} MULTI:{n_multi} REVIEW:{n_review} BLANK:{n_blank}]")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback; traceback.print_exc()


if __name__ == "__main__":
    main()
