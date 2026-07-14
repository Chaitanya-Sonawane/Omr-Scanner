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
"""
import json
import sys
import numpy as np
import cv2

from align import align_sheet, CANON_W, CANON_H

N_DATA_ROWS = 20        # question rows per block
N_OPTION_COLS = 4       # options 1-4
BLOCKS = 2               # left block (Q1-20), right block (Q21-40)
HEADER_ROWS = 2          # "उत्तर पर्याय क्रमांक" label row + "1 2 3 4" row
MIN_GAP = 20              # px, minimum separation to treat two line-peaks as distinct


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


def detect_grid_lines(warped_gray):
    th = cv2.adaptiveThreshold(
        warped_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 25, 10
    )

    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (80, 1))
    horiz = cv2.dilate(cv2.erode(th, horiz_kernel), horiz_kernel)
    row_lines = _detect_lines(horiz.sum(axis=1).astype(np.float64))

    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 80))
    vert = cv2.dilate(cv2.erode(th, vert_kernel), vert_kernel)
    col_lines = _detect_lines(vert.sum(axis=0).astype(np.float64))

    return row_lines, col_lines


def build_template(reference_path, out_path="template.json", debug_path="debug_template_overlay.jpg"):
    img = cv2.imread(reference_path)
    if img is None:
        raise FileNotFoundError(reference_path)

    warped = align_sheet(img, out_size=(CANON_W, CANON_H))
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)

    row_lines, col_lines = detect_grid_lines(gray)
    print(f"Detected {len(row_lines)} horizontal lines, {len(col_lines)} vertical lines.")

    n_row_lines_expected = HEADER_ROWS + N_DATA_ROWS + 1  # +1 outer top border
    n_col_lines_expected = BLOCKS * (1 + N_OPTION_COLS) + 1
    if len(row_lines) != n_row_lines_expected:
        raise RuntimeError(
            f"Expected {n_row_lines_expected} horizontal lines, got {len(row_lines)}. "
            "Inspect debug output / adjust MIN_GAP or adaptiveThreshold params before trusting the template."
        )
    if len(col_lines) != n_col_lines_expected:
        raise RuntimeError(
            f"Expected {n_col_lines_expected} vertical lines, got {len(col_lines)}. "
            "Inspect debug output / adjust MIN_GAP or adaptiveThreshold params before trusting the template."
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

    template = {
        "canon_w": CANON_W,
        "canon_h": CANON_H,
        "radius": radius,
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
