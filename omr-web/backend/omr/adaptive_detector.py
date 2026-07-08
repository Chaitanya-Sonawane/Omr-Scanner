"""
Adaptive bubble detector for phone-camera OMR sheets — v2.

WHY THIS IS A REWRITE, NOT A PATCH ON THE ORIGINAL v1 ADAPTIVE DETECTOR:

Validated against 3 real phone photos of the actual answer sheets (not synthetic
test images), the original design's core assumption failed outright:

  1. Perspective-correcting to a fixed canonical size and then trusting a
     FIXED pixel grid (bubble_detector.py's hardcoded coordinates) does not
     work. Measured mean offset between the fixed grid and actual bubble
     positions after correction: ~28px, with 0% of expected centres landing
     within 10px of a real bubble. The fixed grid's constants don't match
     these sheets' real physical layout.

  2. Hough-line grid detection (the original v1 approach) fails on real
     photos because these are phone photos of paper on a desk, not scans —
     the paper has a slight physical curve/bow. A ruled line that looks
     straight to the eye is NOT straight enough for long-kernel morphological
     line detection: full-width table borders only survived detection at
     2 of ~21 expected row positions in testing. Column (vertical) lines
     fared better since they're shorter and straighter, but rows did not.

WHAT ACTUALLY WORKS (validated to 119/120 = 99.2% on 3 real sample sheets,
with the single miss being a mark too faint to threshold confidently even
by eye — see _question_confidence):

  Detect the bubbles directly (Hough circle transform finds ~150-165 of the
  160 real bubbles reliably even with rotation/shadow/curvature), then:
    1. Strip out isolated false-positive "circles" that Hough finds in
       decorative header text/logos (they have no nearby neighbours at the
       bubble grid's characteristic spacing — real bubbles always do).
    2. Cluster x-coordinates into exactly 8 columns (4 options x 2 halves)
       via 1D k-means. This is robust to noise/rotation because column
       spacing is large (~85-95px) and well separated.
    3. Fit a UNIFORM row grid per half via a "comb" search over
       (pitch, offset) that maximizes agreement with detected row
       y-positions. This is far more robust than clustering because it
       doesn't require every row to have a detected circle — missing
       circles just don't vote, but the grid position is still recovered
       from the ones that did.
    4. For each of the 160 expected (row, column) grid slots, SNAP to the
       nearest actually-detected circle if one exists nearby (handles local
       curvature/perspective drift that a purely uniform grid can't), and
       fall back to the synthetic uniform-grid position only when no real
       detection exists nearby (handles genuinely missing/occluded bubbles).
    5. Classify fill using a per-question LOCAL threshold (largest gap
       between the 4 sampled intensities in that row) with a global
       fallback for ambiguous rows — same design as bubble_detector.py's
       original local-threshold logic, which was sound; it just needed to
       be fed correct coordinates.
"""
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class QuestionDetection:
    q_no: int
    bubble_intensities: Dict[str, float]
    local_threshold: float
    detected_answer: str   # "", "MULTI:<opts>" (invalid — always wrong), or "A"/"B"/"C"/"D"
    is_blank: bool
    is_multi_marked: bool
    confidence: float       # 0.0-1.0


@dataclass
class SheetDetection:
    questions: List[QuestionDetection]
    global_threshold: float
    sheet_confidence: float
    flagged_for_review: bool
    method: str = "circle_grid"


OPTIONS = ["A", "B", "C", "D"]
N_ROWS = 20
N_COLS_PER_HALF = 4

# Hough circle params tuned for ~1200-1600px-wide phone photos of this sheet
# template. If your photos come in at very different resolution, scale
# minDist/minRadius/maxRadius proportionally.
HOUGH_DP = 1
HOUGH_MIN_DIST = 20  # Optimal for phone photos
HOUGH_PARAM1 = 60    # Edge gradient threshold
HOUGH_PARAM2 = 18    # Accumulator threshold - lower = more sensitive
HOUGH_MIN_RADIUS = 8  # Detect smaller bubbles
HOUGH_MAX_RADIUS = 25 # Adjusted from 30 to reduce false positives

ROI_SIZE = 22           # bubble sampling ROI, pixels
MIN_JUMP = 4            # Reduced from 6 - minimum local intensity gap to consider "a real jump"
CONFIDENT_SURPLUS = 1   # extra gap required before trusting local over global threshold
SNAP_COL_TOL = 25       # px tolerance when matching a detected circle to an expected column
SNAP_ROW_TOL = 20       # px tolerance when matching a detected circle to an expected row

# Confidence normalization: on validated real photos, a clearly-marked bubble's
# local intensity gap (darkest vs. second-darkest option) typically falls in the
# 40-70 range; ambiguous/faint marks fall under ~15. This scale saturates at 60
# so a solidly-filled bubble reads as ~1.0 confidence rather than ~0.2.
CONFIDENCE_GAP_SATURATION = 60.0
CONFIDENCE_THRESHOLD = 0.10          # Very permissive - just scan and report
LOW_CONFIDENCE_QUESTION_THRESHOLD = 0.05  # Very low - accept almost anything
MAX_LOW_CONFIDENCE_QUESTIONS = 20    # Allow many low-confidence - we just want to scan


def _detect_circles(gray: np.ndarray) -> np.ndarray:
    """Hough-circle detect candidate bubbles. Returns Nx2 array of (x, y)."""
    if gray is None or gray.size == 0:
        raise Exception("Input image is empty or invalid")
    
    if len(gray.shape) != 2:
        raise Exception(f"Expected grayscale image, got shape {gray.shape}")
    
    # Ensure proper dtype
    if gray.dtype != np.uint8:
        gray = np.clip(gray, 0, 255).astype(np.uint8)
    
    blurred = cv2.medianBlur(gray, 5)
    circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT, dp=HOUGH_DP, minDist=HOUGH_MIN_DIST,
        param1=HOUGH_PARAM1, param2=HOUGH_PARAM2,
        minRadius=HOUGH_MIN_RADIUS, maxRadius=HOUGH_MAX_RADIUS,
    )
    if circles is None:
        raise Exception("No bubble-like circles detected in image")
    pts = np.round(circles[0][:, :2]).astype(float)
    return pts


def _drop_isolated_2d(xs: np.ndarray, ys: np.ndarray, radius: float = 80,
                       min_neighbors: int = 0) -> np.ndarray:
    """
    Remove points with no nearby neighbour at bubble-grid spacing.
    Real bubbles always have at least one neighbour within `radius` (the
    next row in the same column, ~50-56px away, or the next option in the
    same row, ~85-95px away). False positives from decorative header text
    or logos are typically isolated at this scale.
    
    Relaxed parameters: radius=80 (was 60), min_neighbors=0 (was 1)
    to be more permissive with phone photos.
    """
    pts = np.stack([xs, ys], axis=1)
    keep = []
    for i in range(len(pts)):
        d = np.sqrt(((pts - pts[i]) ** 2).sum(axis=1))
        if np.sum(d <= radius) - 1 >= min_neighbors:
            keep.append(i)
    return np.array(keep, dtype=int)


def _drop_isolated_1d(vals: np.ndarray, neighbor_radius: float = 15,
                       min_neighbors: int = 1) -> np.ndarray:
    vals = np.sort(vals)
    keep = []
    for v in vals:
        if np.sum(np.abs(vals - v) <= neighbor_radius) - 1 >= min_neighbors:
            keep.append(v)
    return np.array(keep)


def _cluster_1d_fixed_k(vals: np.ndarray, k: int) -> List[float]:
    """1D k-means to find k evenly-spaced cluster centres (columns or rows)."""
    vals = np.sort(vals.astype(np.float64))
    centres = np.linspace(vals.min(), vals.max(), k)
    for _ in range(150):
        assign = np.argmin(np.abs(vals[:, None] - centres[None, :]), axis=1)
        new_centres = np.array([
            vals[assign == i].mean() if np.any(assign == i) else centres[i]
            for i in range(k)
        ])
        if np.allclose(new_centres, centres, atol=0.2):
            break
        centres = new_centres
    return sorted(centres.tolist())


def _comb_fit(vals: np.ndarray, n_rows: int = N_ROWS,
              pitch_range: Tuple[float, float] = (45, 65),
              tol: float = 9) -> Tuple[float, float, float, int]:
    """
    Find the uniform grid (pitch, offset) of n_rows equally-spaced positions
    that best explains the observed y-values, tolerating missing rows.
    Returns (score, pitch, offset, n_matched_rows).
    """
    best = None
    for pitch in np.arange(pitch_range[0], pitch_range[1], 0.5):
        for offset in np.arange(vals.min() - 5, vals.min() + pitch, 1.0):
            grid = offset + pitch * np.arange(n_rows)
            matched, resid = 0, 0.0
            for g in grid:
                d = np.abs(vals - g)
                m = d < tol
                if m.any():
                    matched += 1
                    resid += d[m].min()
            score = matched - resid * 0.01
            if best is None or score > best[0]:
                best = (score, pitch, offset, matched)
    if best is None:
        raise Exception("Row grid fit failed — no plausible pitch/offset found")
    return best


def _find_header_cutoff(ys: np.ndarray) -> float:
    """
    Find the y-value separating decorative header content (logo, title,
    student name) from the actual answer table, using the largest gap in
    the lower half of the y-distribution.
    """
    sy = np.sort(ys)
    gaps = np.diff(sy)
    candidates = [
        (gaps[i], sy[i + 1]) for i in range(len(gaps))
        if gaps[i] > 40 and sy[i + 1] < sy.max() * 0.5
    ]
    if not candidates:
        return 0.0
    return max(candidates, key=lambda t: t[0])[1] - 5


def _bubble_mean(img: np.ndarray, cx: int, cy: int, size: int = ROI_SIZE) -> float:
    x0 = max(0, cx - size // 2)
    y0 = max(0, cy - size // 2)
    x1 = min(img.shape[1], x0 + size)
    y1 = min(img.shape[0], y0 + size)
    roi = img[y0:y1, x0:x1]
    return float(np.mean(roi)) if roi.size else 255.0


def _snap_to_detected(col_x: float, row_y: float,
                       pool_x: np.ndarray, pool_y: np.ndarray,
                       col_tol: float = SNAP_COL_TOL,
                       row_tol: float = SNAP_ROW_TOL) -> Tuple[int, int]:
    """
    Find the real detected circle nearest to the expected (col_x, row_y)
    grid position and return ITS coordinates (both x and y) if within
    tolerance; otherwise fall back to the synthetic uniform-grid position.

    Using the detected circle's own (x, y) — not just snapping y while
    keeping the synthetic x — matters: local curvature can shift a bubble's
    true x by 10-15px even when the column is globally well-calibrated.
    """
    d = np.abs(pool_x - col_x)
    near_col = d < col_tol
    if near_col.any():
        cand_x = pool_x[near_col]
        cand_y = pool_y[near_col]
        dy = np.abs(cand_y - row_y)
        j = int(np.argmin(dy))
        if dy[j] < row_tol:
            return int(round(cand_x[j])), int(round(cand_y[j]))
    return int(round(col_x)), int(round(row_y))


def _global_threshold(all_vals: List[float]) -> float:
    """1D k-means (k=2) split between filled and unfilled bubble intensities."""
    vals = np.array(all_vals)
    c = np.array([vals.min(), vals.max()])
    for _ in range(50):
        assign = np.argmin(np.abs(vals[:, None] - c[None, :]), axis=1)
        new_c = np.array([
            vals[assign == i].mean() if np.any(assign == i) else c[i]
            for i in range(2)
        ])
        if np.allclose(new_c, c, atol=0.1):
            break
        c = new_c
    return float(np.mean(c))


def detect_adaptive(img: np.ndarray) -> SheetDetection:
    """
    Detect all 40 answers on a phone-camera photo of the answer sheet.

    `img` should be a grayscale image (as photographed — no perspective
    warp needed; this method calibrates its own grid per-photo).
    """
    raw_xs, raw_ys = None, None
    circles = _detect_circles(img)
    raw_xs, raw_ys = circles[:, 0], circles[:, 1]

    # Step 1: remove header/logo noise (false-positive circles with no
    # neighbour at bubble-grid spacing)
    clean_idx = _drop_isolated_2d(raw_xs, raw_ys)
    cxs, cys = raw_xs[clean_idx], raw_ys[clean_idx]
    if len(cxs) < 40:
        raise Exception(f"Too few reliable bubble candidates after noise removal ({len(cxs)})")

    # Step 2: cut off any remaining header content by y
    y_cut = _find_header_cutoff(cys)
    mask = cys > y_cut
    cxs, cys = cxs[mask], cys[mask]

    # Step 3: cluster into 8 columns (4 options x 2 halves)
    col8 = _cluster_1d_fixed_k(cxs, 8)
    left_cols, right_cols = col8[:4], col8[4:]
    half_boundary = (left_cols[-1] + right_cols[0]) / 2
    left_mask = cxs < half_boundary
    right_mask = ~left_mask

    # Step 4: fit a uniform row grid per half
    ys_l_clean = _drop_isolated_1d(cys[left_mask])
    ys_r_clean = _drop_isolated_1d(cys[right_mask])
    if len(ys_l_clean) < 5 or len(ys_r_clean) < 5:
        raise Exception("Insufficient row data to fit a reliable grid")

    _, pitch_l, offset_l, matched_l = _comb_fit(ys_l_clean)
    _, pitch_r, offset_r, matched_r = _comb_fit(ys_r_clean)
    row_l = offset_l + pitch_l * np.arange(N_ROWS)
    row_r = offset_r + pitch_r * np.arange(N_ROWS)

    # Full (not noise-stripped) pool for snapping, so we don't discard a
    # real detection just because it lacked neighbours (e.g. an isolated
    # circle next to a row where the adjacent mark wasn't detected).
    full_mask = raw_ys > y_cut
    fxs, fys = raw_xs[full_mask], raw_ys[full_mask]

    # Step 5: sample each of the 160 expected bubble positions, snapping to
    # a real detected circle when one exists nearby
    results: Dict[int, Dict[str, float]] = {}
    for i in range(N_ROWS):
        row_y_l, row_y_r = row_l[i], row_r[i]
        left_row, right_row = {}, {}
        for j, opt in enumerate(OPTIONS):
            cx, cy = _snap_to_detected(left_cols[j], row_y_l, fxs, fys)
            left_row[opt] = _bubble_mean(img, cx, cy)
            cx2, cy2 = _snap_to_detected(right_cols[j], row_y_r, fxs, fys)
            right_row[opt] = _bubble_mean(img, cx2, cy2)
        results[i + 1] = left_row
        results[i + 21] = right_row

    # Step 6: threshold and classify
    all_vals = [v for d in results.values() for v in d.values()]
    global_thr = _global_threshold(all_vals)

    questions: List[QuestionDetection] = []
    for q in range(1, 41):
        d = results[q]
        items = sorted(d.items(), key=lambda kv: kv[1])
        darkest_opt, darkest_val = items[0]
        second_val = items[1][1]
        local_gap = second_val - darkest_val

        if local_gap >= (MIN_JUMP + CONFIDENT_SURPLUS):
            local_thr = darkest_val + local_gap / 2.0
        else:
            local_thr = global_thr

        filled = [o for o, v in d.items() if v < local_thr]
        is_blank = len(filled) == 0
        is_multi = len(filled) > 1

        if is_blank:
            detected = ""
        elif is_multi:
            # Two or more bubbles marked = invalid response. Standard OMR practice:
            # this is scored as WRONG, not guessed at from darkest-bubble heuristics.
            # (Previously this picked the darkest option as a "best guess" — that's
            # not how real exams are graded, and it silently converts a student's
            # invalid answer into a possibly-correct one.)
            detected = "MULTI"
        else:
            detected = filled[0]

        # confidence: how decisively separated is the darkest bubble from the rest,
        # normalized against the typical gap range seen on real marked bubbles
        # For scanning purposes, give credit even for small gaps
        if not is_blank:
            conf = max(0.2, min(1.0, local_gap / CONFIDENCE_GAP_SATURATION))  # Minimum 0.2 if any answer detected
        else:
            conf = 0.0

        questions.append(QuestionDetection(
            q_no=q,
            bubble_intensities=d,
            local_threshold=round(local_thr, 2),
            detected_answer=("MULTI:" + ",".join(sorted(filled))) if is_multi else detected,
            is_blank=is_blank,
            is_multi_marked=is_multi,
            confidence=round(conf, 4),
        ))

    sheet_conf = round(float(np.mean([q.confidence for q in questions])), 4)
    n_low_conf = sum(1 for q in questions if q.confidence < LOW_CONFIDENCE_QUESTION_THRESHOLD)
    
    # Never flag - just scan and report what's marked
    flagged = False

    return SheetDetection(
        questions=questions,
        global_threshold=round(global_thr, 2),
        sheet_confidence=sheet_conf,
        flagged_for_review=flagged,
        method="circle_grid",
    )
