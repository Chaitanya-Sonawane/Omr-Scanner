"""
scan_omr.py
-----------
Production OMR reader for the NMMS-style 40-question / 4-option sheet.

Pipeline per sheet (no fresh circle detection ever happens here):
  1. align_sheet()      -> warp photo into the canonical frame using the
                            outer table border as anchor points.
  2. load template.json -> 160 fixed (x, y) bubble centers, built once.
  3. sample fill-intensity at each of the 160 known coordinates.
  4. compute a PER-SHEET adaptive threshold from that sheet's own
     lightest/darkest bubbles (never a hardcoded global constant).
  5. classify each question as a clean single answer, BLANK, MULTI, or
     REVIEW (ambiguous / too close to the threshold to trust). The code
     never silently guesses on a close call.

Usage:
    python3 scan_omr.py sheet1.jpg sheet2.jpg ... --out omr_results.xlsx
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from align import align_sheet, CANON_W, CANON_H

TEMPLATE_PATH = "template.json"
N_QUESTIONS = 40
N_OPTIONS = 4

# How close two candidate darkness scores must be to call it MULTI vs a
# genuine single mark, and how close a single score must be to the
# threshold to be untrustworthy and get flagged REVIEW instead of guessed.
MULTI_MARGIN = 0.12     # fraction of the sheet's fill-value range
REVIEW_MARGIN = 0.06    # fraction of the sheet's fill-value range


def load_template(path=TEMPLATE_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def sample_fill(gray, x, y, radius):
    """
    Mean darkness (0=white .. 255=pure black) inside a circular ROI a bit
    smaller than the bubble radius, so we sample ink and not the outline.
    """
    r = max(4, int(radius * 0.72))
    x0, x1 = max(0, x - r), min(gray.shape[1], x + r)
    y0, y1 = max(0, y - r), min(gray.shape[0], y + r)
    patch = gray[y0:y1, x0:x1]
    if patch.size == 0:
        return 0.0
    mask = np.zeros(patch.shape, dtype=np.uint8)
    cv2.circle(mask, (patch.shape[1] // 2, patch.shape[0] // 2), r, 255, -1)
    vals = patch[mask == 255]
    if vals.size == 0:
        return 0.0
    # invert so higher = darker = more filled
    return float(255 - vals.mean())


def per_sheet_threshold(all_scores):
    """
    Derive a fill/no-fill threshold from THIS sheet's own score
    distribution rather than a global constant, so lighting/pen/scan
    differences between sheets don't need separate tuning.
    Uses Otsu's method on the 160 scores for that sheet.
    """
    scores = np.array(all_scores, dtype=np.float32)
    scores_8u = np.clip(scores, 0, 255).astype(np.uint8)
    thresh_val, _ = cv2.threshold(scores_8u, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return float(thresh_val), float(scores.min()), float(scores.max())


def classify_question(scores, threshold, score_range):
    """
    scores: list of 4 darkness values for options 1-4.
    Returns (selected_option_or_None, status) where status in
    {"OK", "BLANK", "MULTI", "REVIEW"}.
    """
    rng = max(score_range, 1e-6)
    filled = [i for i, s in enumerate(scores) if s >= threshold]

    if len(filled) == 0:
        return None, "BLANK"

    if len(filled) >= 2:
        # confirm it's genuinely two dark bubbles, not one dark + one
        # borderline noise pixel cluster
        sorted_scores = sorted(scores, reverse=True)
        gap = (sorted_scores[0] - sorted_scores[1]) / rng
        if gap < MULTI_MARGIN:
            return None, "MULTI"
        # top one clearly darker than the rest -> treat as single, but
        # only if it also clears the REVIEW margin below
        filled = [int(np.argmax(scores))]

    best_idx = filled[0]
    best_score = scores[best_idx]
    margin_to_threshold = (best_score - threshold) / rng
    others = [s for i, s in enumerate(scores) if i != best_idx]
    margin_to_next = (best_score - max(others)) / rng if others else 1.0

    if margin_to_threshold < REVIEW_MARGIN or margin_to_next < REVIEW_MARGIN:
        return best_idx + 1, "REVIEW"

    return best_idx + 1, "OK"


def scan_sheet(image_path, template, debug_dir=None):
    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(image_path)

    warped = align_sheet(img, out_size=(template["canon_w"], template["canon_h"]))
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    radius = template["radius"]

    # 1. sample all 160 bubbles
    raw_scores = {}
    for key, c in template["bubbles"].items():
        raw_scores[key] = sample_fill(gray, int(round(c["x"])), int(round(c["y"])), radius)

    # 2. per-sheet adaptive threshold from this sheet's own distribution
    threshold, smin, smax = per_sheet_threshold(list(raw_scores.values()))
    score_range = smax - smin

    # 3. classify each question
    rows = []
    for q in range(1, N_QUESTIONS + 1):
        scores = [raw_scores[f"{q}_{opt}"] for opt in range(1, N_OPTIONS + 1)]
        selected, status = classify_question(scores, threshold, score_range)
        rows.append({
            "Question": q,
            "Selected_Option": selected if selected is not None else "",
            "Status": status,
        })

    if debug_dir:
        dbg = warped.copy()
        for q in range(1, N_QUESTIONS + 1):
            row = rows[q - 1]
            for opt in range(1, N_OPTIONS + 1):
                c = template["bubbles"][f"{q}_{opt}"]
                x, y = int(c["x"]), int(c["y"])
                if row["Status"] == "MULTI":
                    color = (0, 0, 255)
                elif row["Status"] == "REVIEW":
                    color = (0, 165, 255)
                elif row["Selected_Option"] == opt:
                    color = (0, 200, 0)
                else:
                    color = (200, 200, 200)
                cv2.circle(dbg, (x, y), radius, color, 2)
        Path(debug_dir).mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(Path(debug_dir) / f"{Path(image_path).stem}_debug.jpg"), dbg)

    return rows, {"threshold": threshold, "score_min": smin, "score_max": smax}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+", help="Sheet photo(s) to scan")
    ap.add_argument("--out", default="omr_results.xlsx")
    ap.add_argument("--debug-dir", default="debug_overlays")
    args = ap.parse_args()

    template = load_template()

    all_sheets = {}
    summary_rows = []
    for img_path in args.images:
        name = Path(img_path).stem
        try:
            rows, meta = scan_sheet(img_path, template, debug_dir=args.debug_dir)
        except Exception as e:
            print(f"[FAILED] {img_path}: {e}", file=sys.stderr)
            summary_rows.append({"Sheet": name, "Status": f"FAILED: {e}"})
            continue

        df = pd.DataFrame(rows)
        all_sheets[name[:31]] = df  # Excel sheet name char limit

        n_review = (df["Status"] == "REVIEW").sum()
        n_multi = (df["Status"] == "MULTI").sum()
        n_blank = (df["Status"] == "BLANK").sum()
        n_ok = (df["Status"] == "OK").sum()
        summary_rows.append({
            "Sheet": name, "OK": n_ok, "Blank": n_blank,
            "Multi": n_multi, "Review": n_review,
            "Threshold": round(meta["threshold"], 1),
        })
        print(f"{name}: OK={n_ok} BLANK={n_blank} MULTI={n_multi} REVIEW={n_review}")

    with pd.ExcelWriter(args.out, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Summary", index=False)
        for name, df in all_sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)

    print(f"\nWrote {args.out}")
    if any(r.get("Review", 0) or r.get("Multi", 0) for r in summary_rows):
        print("NOTE: sheets contain REVIEW/MULTI rows that need manual eyes - "
              f"check {args.debug_dir}/ overlays before trusting scores.")


if __name__ == "__main__":
    main()
