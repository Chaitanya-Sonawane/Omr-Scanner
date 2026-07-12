"""
calibrate_template.py
----------------------
RUN THIS ONCE (or once per sheet layout/print design). Never run per scan.

Takes the cleanest available reference sheet, aligns it into canonical
space (align.py), then locates the printed table gridlines on that ONE
image (horizontal row-dividers, vertical column-dividers). Because the
sheet is a printed form, the gridlines are exact and far more reliable
anchors than trying to Hough-detect 160 individual bubble circles - each
bubble center is simply the midpoint of its row/column cell.

The resulting coordinates are written to template.json, which is the
permanent source of truth used by scan_omr.py for every future sheet.
No geometry detection ever happens again after this step.

Hardening added on top of the original architecture:
  - EXIF-aware loading and an up-front blur/alignment-confidence check, so
    a bad reference photo is rejected before it poisons every future scan.
  - A small sweep of adaptiveThreshold parameters is tried automatically
    if the expected line count isn't found on the first attempt, instead
    of a single hard-coded parameter set.
  - Row-height / column-width uniformity is validated (coefficient of
    variation) to catch a spurious extra/missing line that happens to
    match the expected COUNT but not the expected SPACING.
"""
import json
import sys

import numpy as np
import cv2

from align import align_sheet, load_image, CANON_W, CANON_H

N_DATA_ROWS = 20        # question rows per block
N_OPTION_COLS = 4       # options 1-4
BLOCKS = 2               # left block (Q1-20), right block (Q21-40)
HEADER_ROWS = 2          # "उत्तर पर्याय क्रमांक" label row + "1 2 3 4" row
MIN_GAP = 20              # px, minimum separation to treat two line-peaks as distinct

# (adaptiveThreshold blockSize, C) parameter sets tried in order until the
# expected grid-line counts are found. The tighter values are tried first
# since they work on most clean photos; the wider values are a recovery
# path for noisier real-world photos where a tight block size just picks
# up paper texture/shadow noise instead of isolating the printed lines.
PARAM_SWEEP = [
    (25, 10), (35, 15), (45, 20), (25, 20), (45, 10),
    (55, 20), (65, 20), (75, 25), (91, 25), (31, 15), (51, 20),
]

MAX_SPACING_CV = 0.25  # coefficient of variation allowed in row/col spacing


def _detect_lines(mask_1d, min_gap=MIN_GAP):
    """Find local maxima (line positions) in a 1-D projection profile."""
    peaks = []
    thresh = mask_1d.max() * 0.5
    for i in range(1, len(mask_1d) - 1):
        if mask_1d[i] > thresh and mask_1d[i] >= mask_1d[i - 1] and mask_1d[i] >= mask_1d[i + 1]:
            peaks.append(i)
    dedup = []
    for p in peaks:
        if not dedup or p - dedup[-1] > min_gap:
            dedup.append(p)
        else:
            dedup[-1] = (dedup[-1] + p) // 2  # merge near-duplicates
    return dedup


GRID_PAD = 40  # px; outer border lines land exactly at the canvas edge by
                # construction of the warp, leaving erosion no margin to see
                # them - padding restores that margin on both sides.


def detect_grid_lines(warped_gray, block_size, c_val):
    padded = cv2.copyMakeBorder(
        warped_gray, GRID_PAD, GRID_PAD, GRID_PAD, GRID_PAD,
        cv2.BORDER_CONSTANT, value=255
    )
    th = cv2.adaptiveThreshold(
        padded, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, block_size, c_val
    )

    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (80, 1))
    horiz = cv2.dilate(cv2.erode(th, horiz_kernel), horiz_kernel)
    row_lines = _detect_lines(horiz.sum(axis=1).astype(np.float64))

    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 80))
    vert = cv2.dilate(cv2.erode(th, vert_kernel), vert_kernel)
    col_lines = _detect_lines(vert.sum(axis=0).astype(np.float64))

    # Map back from padded coordinates to the original warped-image frame.
    row_lines = [r - GRID_PAD for r in row_lines]
    col_lines = [c - GRID_PAD for c in col_lines]
    return row_lines, col_lines


def _spacing_cv(positions):
    """Coefficient of variation of consecutive gaps - flags uneven grids
    that happen to have the right line COUNT but wrong SPACING (a sign
    that one or more detected 'lines' are spurious)."""
    diffs = np.diff(positions)
    if diffs.size == 0 or diffs.mean() == 0:
        return 1.0
    return float(diffs.std() / diffs.mean())


def build_template(reference_path, out_path="template.json", debug_path="debug_template_overlay.jpg"):
    img = load_image(reference_path)
    if img is None:
        raise FileNotFoundError(reference_path)

    warped, quality = align_sheet(img, out_size=(CANON_W, CANON_H))
    print(f"Alignment quality on reference sheet: {quality}")
    if not quality["blur_ok"]:
        raise RuntimeError(
            f"Reference sheet looks blurry/out of focus (blur_score={quality['blur_score']}). "
            "Use a sharper reference photo before calibrating - every future scan depends on this template."
        )
    if quality["border_confidence"] == "low":
        raise RuntimeError(
            "Could not confidently locate the sheet's outer border on the reference photo "
            "(fell back to full-frame). Retake the reference photo with clear margins around the table."
        )

    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)

    n_row_lines_expected = HEADER_ROWS + N_DATA_ROWS + 1  # +1 outer top border
    n_col_lines_expected = BLOCKS * (1 + N_OPTION_COLS) + 1

    row_lines, col_lines = [], []
    used_params = None
    for block_size, c_val in PARAM_SWEEP:
        r, c = detect_grid_lines(gray, block_size, c_val)
        if len(r) == n_row_lines_expected and len(c) == n_col_lines_expected:
            row_lines, col_lines = r, c
            used_params = (block_size, c_val)
            break
        # keep the closest-count attempt around for a useful error message
        if not row_lines or (abs(len(r) - n_row_lines_expected) + abs(len(c) - n_col_lines_expected) <
                              abs(len(row_lines) - n_row_lines_expected) + abs(len(col_lines) - n_col_lines_expected)):
            row_lines, col_lines = r, c

    if used_params is None:
        raise RuntimeError(
            f"Expected {n_row_lines_expected} horizontal / {n_col_lines_expected} vertical gridlines; "
            f"best attempt found {len(row_lines)} / {len(col_lines)} after trying {len(PARAM_SWEEP)} "
            "threshold parameter sets. Inspect debug output / the reference photo before trusting a template."
        )
    print(f"Detected {len(row_lines)} horizontal, {len(col_lines)} vertical lines "
          f"(adaptiveThreshold blockSize={used_params[0]}, C={used_params[1]}).")

    # Sanity-check spacing uniformity - catches a spurious line that
    # coincidentally makes the total COUNT match.
    row_cv = _spacing_cv(row_lines)
    col_cv = _spacing_cv(col_lines)
    if row_cv > MAX_SPACING_CV or col_cv > MAX_SPACING_CV:
        raise RuntimeError(
            f"Grid line counts matched but spacing is too irregular (row CV={row_cv:.2f}, "
            f"col CV={col_cv:.2f}, max allowed {MAX_SPACING_CV}). This usually means a shadow or "
            "stray mark was mistaken for a gridline - inspect the reference photo before trusting this template."
        )

    # Data rows start after the header rows (skip the first HEADER_ROWS boundaries' worth)
    data_row_boundaries = row_lines[HEADER_ROWS:]  # N_DATA_ROWS + 1 values
    row_centers = [
        (data_row_boundaries[i] + data_row_boundaries[i + 1]) / 2
        for i in range(N_DATA_ROWS)
    ]

    # Column boundaries: [Qcol | opt1 opt2 opt3 opt4] x BLOCKS
    col_centers_by_block = []
    for b in range(BLOCKS):
        base = b * (1 + N_OPTION_COLS)
        block_bounds = col_lines[base: base + 1 + N_OPTION_COLS + 1]  # Qcol + 4 opts -> 6 boundaries
        opt_bounds = block_bounds[1:]  # drop the Qcol/opt1 divider region, keep opt1..opt4 boundaries
        centers = [(opt_bounds[i] + opt_bounds[i + 1]) / 2 for i in range(N_OPTION_COLS)]
        col_centers_by_block.append(centers)

    # bubble radius: ~40% of the smaller of row-height / col-width, gives a safe inner sampling ring
    row_h = np.median(np.diff(data_row_boundaries))
    col_w = np.median(np.diff(col_lines))
    radius = int(round(0.36 * min(row_h, col_w)))

    # Column-line index ranges for each question-block (matches the
    # `block_bounds = col_lines[base : base + 1 + N_OPTION_COLS + 1]` slicing
    # used above). Persisted so scan-time grid_correct() can fit each
    # block's own scale/offset independently instead of one line across the
    # full table width - the left (Q1-20) and right (Q21-40) blocks are
    # visually separate halves and can pick up non-uniform distortion
    # (lens distortion, page curl through the middle) differently.
    col_block_ranges = [
        [b * (1 + N_OPTION_COLS), b * (1 + N_OPTION_COLS) + N_OPTION_COLS + 2]
        for b in range(BLOCKS)
    ]

    template = {
        "canon_w": CANON_W,
        "canon_h": CANON_H,
        "radius": radius,
        "ref_row_lines": [float(v) for v in row_lines],
        "ref_col_lines": [float(v) for v in col_lines],
        "col_block_ranges": col_block_ranges,
        "bubbles": {}
    }
    for r in range(N_DATA_ROWS):
        y = float(row_centers[r])
        for block in range(BLOCKS):
            q_num = r + 1 + block * N_DATA_ROWS
            for opt in range(N_OPTION_COLS):
                x = float(col_centers_by_block[block][opt])
                template["bubbles"][f"{q_num}_{opt + 1}"] = {"x": round(x, 1), "y": round(y, 1)}

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path} with {len(template['bubbles'])} bubble coordinates. radius={radius}")

    dbg = warped.copy()
    for key, c in template["bubbles"].items():
        cv2.circle(dbg, (int(c["x"]), int(c["y"])), radius, (0, 0, 255), 2)
    cv2.imwrite(debug_path, dbg)
    print(f"Wrote {debug_path} for visual verification.")

    return template


if __name__ == "__main__":
    ref = sys.argv[1] if len(sys.argv) > 1 else "reference_sheet.jpg"
    build_template(ref)
