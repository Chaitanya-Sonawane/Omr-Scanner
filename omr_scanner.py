"""
OMR Scanner v3.0
Detects filled bubbles in 40-question, 4-option OMR answer sheets.

Improvements over v2:
  - Uses enhancer.preprocess_for_omr() for consistent, shadow-free preprocessing
  - HOUGH_GRADIENT_ALT tried first (OpenCV >= 4.5.1) for sub-pixel accuracy
  - Improved deskew using Shi-Tomasi corners to focus on meaningful regions
  - Cleaner two-pass verification — thresholds calibrated to blank baseline
  - Confidence formula tied directly to measured signal (no flat bonus)
  - Explicit 'no_clear_mark' flag instead of silent None return
"""

import cv2
import numpy as np
import sys
from typing import Dict, List, Optional, Tuple

from enhancer import preprocess_for_omr

DEBUG_ENABLED = False


def _log(msg: str) -> None:
    if DEBUG_ENABLED:
        print(f"[OMR] {msg}")


# ---------------------------------------------------------------------------
# Circle detection
# ---------------------------------------------------------------------------

def _try_hough(img: np.ndarray, min_r: int, max_r: int, param2: float,
               method: int = cv2.HOUGH_GRADIENT) -> Optional[np.ndarray]:
    return cv2.HoughCircles(
        img, method, dp=1, minDist=16,
        param1=50, param2=param2,
        minRadius=min_r, maxRadius=max_r,
    )


def _detect_circles(gray: np.ndarray) -> Tuple[Optional[np.ndarray], np.ndarray]:
    """
    Multi-stage Hough circle detection with four fallback strategies.

    Stage 1: HOUGH_GRADIENT_ALT (OpenCV >= 4.5.1) — sub-pixel accurate.
    Stage 2: Classic HOUGH_GRADIENT on median-blurred image.
    Stage 3: Bilateral filter to preserve edges while reducing noise.
    Stage 4: Aggressive CLAHE + Otsu binarisation for low-quality photos.
    """
    h, w = gray.shape
    r_est = max(8, min(30, w // 80))
    min_r, max_r = max(5, r_est - 7), r_est + 12

    blur = cv2.medianBlur(gray, 5)

    # Stage 1: HOUGH_GRADIENT_ALT
    try:
        alt = cv2.HOUGH_GRADIENT_ALT
        for p2 in [0.85, 0.75, 0.65, 0.55]:
            c = _try_hough(blur, min_r, max_r, p2, alt)
            if c is not None and len(c[0]) >= 8:
                return c, blur
    except AttributeError:
        pass  # OpenCV < 4.5.1

    # Stage 2: Classic gradient, decreasing threshold
    for p2 in [22, 18, 14, 10, 8]:
        c = _try_hough(blur, min_r, max_r, p2)
        if c is not None and len(c[0]) >= 8:
            return c, blur

    # Stage 3: Bilateral filter
    bilat = cv2.bilateralFilter(gray, 9, 75, 75)
    blur3 = cv2.medianBlur(bilat, 3)
    for p2 in [18, 14, 10, 7]:
        c = _try_hough(blur3, min_r, max_r, p2)
        if c is not None and len(c[0]) >= 8:
            return c, blur3

    # Stage 4: Aggressive CLAHE + Otsu
    eq = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8)).apply(gray)
    _, bw = cv2.threshold(eq, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    blur4 = cv2.medianBlur(bw, 3)
    for p2 in [15, 10, 7, 5]:
        c = _try_hough(blur4, max(4, r_est - 9), r_est + 15, p2)
        if c is not None and len(c[0]) >= 8:
            return c, blur4

    return None, blur


# ---------------------------------------------------------------------------
# Rotation correction
# ---------------------------------------------------------------------------

def _auto_rotate(img: np.ndarray, gray: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Correct small skew (<= 15 deg) using dominant Hough line angle.
    Shi-Tomasi corners focus the edge map on meaningful sheet structure.
    """
    corners = cv2.goodFeaturesToTrack(gray, maxCorners=300, qualityLevel=0.01,
                                      minDistance=10)
    mask = np.zeros_like(gray)
    if corners is not None:
        for pt in corners:
            x, y = pt.ravel().astype(int)
            cv2.circle(mask, (x, y), 12, 255, -1)
    else:
        mask[:] = 255

    edges = cv2.bitwise_and(cv2.Canny(gray, 40, 120), mask)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180,
                             threshold=80, minLineLength=80, maxLineGap=15)
    if lines is None or len(lines) < 5:
        return img, gray

    angles = [
        np.degrees(np.arctan2(l[0][3] - l[0][1], l[0][2] - l[0][0]))
        for l in lines[:100]
        if abs(np.degrees(np.arctan2(l[0][3] - l[0][1], l[0][2] - l[0][0]))) <= 15
    ]
    if not angles:
        return img, gray

    skew = float(np.median(angles))
    if abs(skew) < 0.4:
        return img, gray

    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), skew, 1.0)
    img_r = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC,
                            borderMode=cv2.BORDER_REPLICATE)
    _log(f"Auto-rotated {skew:.2f} deg")
    return img_r, cv2.cvtColor(img_r, cv2.COLOR_BGR2GRAY)


# ---------------------------------------------------------------------------
# Grid construction
# ---------------------------------------------------------------------------

def _safe_kmeans(data: np.ndarray, k: int, criteria: tuple, attempts: int = 10):
    if len(data) < k:
        return None, None
    _, labels, centers = cv2.kmeans(data, k, None, criteria, attempts,
                                    cv2.KMEANS_PP_CENTERS)
    return labels, centers


def _compute_row_y(all_pts: np.ndarray) -> List[float]:
    """
    Estimate 20 shared row Y-positions by K-means on ALL bubble Y-coords
    (both blocks pooled).  A polyfit pass snaps outlier rows onto the line.
    """
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, 0.1)
    ys = all_pts[:, 1].reshape(-1, 1).astype(np.float32)
    labels, centers = _safe_kmeans(ys, min(20, len(ys)), criteria)

    if labels is None:
        return np.linspace(float(ys.min()), float(ys.max()), 20).tolist()

    row_y = sorted(float(c) for c in centers.flatten())
    if len(row_y) < 20:
        diffs = np.diff(row_y)
        pitch = float(np.median(diffs[diffs > 3])) if any(diffs > 3) else 30.0
        while len(row_y) < 20:
            row_y.append(row_y[-1] + pitch)

    # Polyfit outlier snapping (two passes)
    idx = np.arange(20, dtype=np.float64)
    arr = np.array(row_y, dtype=np.float64)
    diffs = np.diff(arr)
    pitch = float(np.median(diffs[diffs > 3])) if any(diffs > 3) else 30.0
    for _ in range(2):
        a, b = np.polyfit(idx, arr, 1)
        fitted = a * idx + b
        bad = np.abs(arr - fitted) > max(pitch * 0.4, 8)
        if not bad.any():
            break
        arr[bad] = fitted[bad]

    return arr.tolist()


def _build_grid(block_pts: np.ndarray, gray: np.ndarray,
                radius_est: int, row_y: List[float]) -> Dict[int, List[Tuple[int, int]]]:
    """
    Build a 20x4 grid of (x, y) sample centres for one answer block.
    Per-column linear regression x = a*row_idx + b tracks perspective drift.
    """
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, 0.1)
    h, w = gray.shape
    bxs = block_pts[:, 0].reshape(-1, 1).astype(np.float32)
    n_cols = min(4, len(block_pts))
    col_labels, col_centers = _safe_kmeans(bxs, n_cols, criteria)

    if col_labels is None or n_cols < 4:
        col_centers_list = np.linspace(float(bxs.min()), float(bxs.max()), 4).tolist()
        col_labels_arr = np.zeros((len(block_pts), 1), dtype=np.int32)
        cluster_to_opt = {0: 0}
    else:
        order = np.argsort(col_centers.flatten())
        col_centers_list = sorted(col_centers.flatten().tolist())
        cluster_to_opt = {int(order[i]): i for i in range(len(order))}
        col_labels_arr = col_labels

    col_pts: Dict[int, list] = {i: [] for i in range(4)}
    for i, pt in enumerate(block_pts):
        opt = cluster_to_opt.get(int(col_labels_arr[i][0]), -1)
        if 0 <= opt < 4:
            col_pts[opt].append(pt)

    row_y_arr = np.array(row_y, dtype=np.float64)
    grid: Dict[int, List[Tuple[int, int]]] = {}

    for opt in range(4):
        pts_list = col_pts[opt]
        if len(pts_list) >= 2:
            px = np.array([p[0] for p in pts_list], dtype=np.float64)
            py = np.array([p[1] for p in pts_list], dtype=np.float64)
            ri_of_pt = np.array([int(np.argmin(np.abs(row_y_arr - yp))) for yp in py])
            if len(np.unique(ri_of_pt)) >= 2:
                a, b = np.polyfit(ri_of_pt, px, 1)
            else:
                a, b = 0.0, float(np.median(px))
        else:
            a, b = 0.0, (col_centers_list[opt] if opt < len(col_centers_list) else 0.0)

        col_grid = []
        for ri in range(20):
            gx = int(round(a * ri + b))
            gy = int(round(row_y[ri]))
            gx = max(radius_est, min(w - radius_est - 1, gx))
            gy = max(radius_est, min(h - radius_est - 1, gy))
            col_grid.append((gx, gy))
        grid[opt] = col_grid

    return grid


# ---------------------------------------------------------------------------
# Main detection function
# ---------------------------------------------------------------------------

def detect_bubbles(
    img_path: str,
    debug_out: Optional[str] = None,
) -> Tuple[
    Dict[int, Optional[int]],
    Dict[int, str],
    Dict[int, Dict[int, float]],
    Dict[int, float],
]:
    """
    Detect filled bubbles in a 40-question / 4-option OMR answer sheet.

    Returns
    -------
    answers         : {question: option (1-4) or None}
    flags           : {question: 'low_confidence'|'multi_mark'|'row_smudged'|'no_clear_mark'}
    raw_intensities : {question: {option: mean_gray_value}}
    confidence      : {question: score 0-100}
    """
    img = cv2.imread(img_path)
    if img is None:
        raise RuntimeError(f"Could not read image: {img_path}")

    # Preprocessed grayscale via enhancer (shadow removal, CLAHE, sharpening, deskew)
    gray = preprocess_for_omr(img_path)
    img, gray = _auto_rotate(img, gray)
    h, w = gray.shape

    # --- Circle detection ---
    raw_circles, _ = _detect_circles(gray)
    if raw_circles is None:
        raise RuntimeError(
            f"No circles detected in '{img_path}'. "
            "Ensure the image shows a clear OMR sheet with visible bubbles."
        )

    circles = np.round(raw_circles[0]).astype(int).tolist()

    # Remove circles too close to image borders
    circles = [c for c in circles if 40 < c[0] < w - 40 and 150 < c[1] < h - 20]
    if len(circles) < 8:
        raise RuntimeError(f"Too few circles after border filter ({len(circles)}).")

    # Keep only circles near the median radius
    radii = np.array([c[2] for c in circles])
    r_med = float(np.median(radii))
    circles = [c for c in circles if abs(c[2] - r_med) <= max(2.5, r_med * 0.35)]
    if len(circles) < 8:
        raise RuntimeError(f"Too few circles after radius filter ({len(circles)}).")

    # Drop header debris (logo/stamp) using the largest vertical gap
    ys = sorted(c[1] for c in circles)
    n_total = len(ys)
    cut_y, best_gap = None, 0
    for i in range(1, min(60, n_total)):
        gap = ys[i] - ys[i - 1]
        if gap > 55 and gap > best_gap:
            remaining = sum(1 for y in ys if y >= ys[i])
            if remaining >= max(8, n_total * 0.55):
                best_gap = gap
                cut_y = ys[i]
    if cut_y is not None:
        circles = [c for c in circles if c[1] >= cut_y]
    if len(circles) < 8:
        raise RuntimeError(f"Too few circles after header removal ({len(circles)}).")

    pts = np.array([[c[0], c[1]] for c in circles])
    radius_est = int(np.median([c[2] for c in circles]))

    # Hard X-midpoint split — avoids k-means being thrown off by the
    # printed question-number column between the two answer grids.
    block_ids = np.where(pts[:, 0] < w / 2.0, 0, 1)

    row_y = _compute_row_y(pts)
    sample_r = max(int(radius_est * 0.60), 6)

    # Otsu binary map for filled-pixel ratio
    _, gray_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    raw_intensities: Dict[int, Dict[int, float]] = {}
    bubble_details: Dict[int, Dict[int, dict]] = {}
    debug_img = img.copy()

    for block_id, q_offset in [(0, 0), (1, 20)]:
        block_pts = pts[block_ids == block_id]

        if len(block_pts) < 4:
            for ri in range(20):
                q = ri + 1 + q_offset
                raw_intensities[q] = {o: 255.0 for o in range(1, 5)}
                bubble_details[q] = {o: {'mean': 255.0, 'filled_ratio': 0.0}
                                     for o in range(1, 5)}
            continue

        col_grid = _build_grid(block_pts, gray, radius_est, row_y)

        for ri in range(20):
            q = ri + 1 + q_offset
            raw_intensities[q] = {}
            bubble_details[q] = {}

            for opt_idx in range(4):
                cx, cy = col_grid[opt_idx][ri]
                circ_mask = np.zeros(gray.shape, dtype=np.uint8)
                cv2.circle(circ_mask, (cx, cy), sample_r, 255, -1)

                mean_val = float(cv2.mean(gray, mask=circ_mask)[0])

                dark_px = cv2.countNonZero(
                    cv2.bitwise_and(cv2.bitwise_not(gray_otsu), circ_mask)
                )
                total_px = cv2.countNonZero(circ_mask)
                fill_ratio = dark_px / (total_px + 1e-9)

                opt = opt_idx + 1
                raw_intensities[q][opt] = mean_val
                bubble_details[q][opt] = {'mean': mean_val, 'filled_ratio': fill_ratio}

                if debug_out:
                    colour = (0, 200, 0) if fill_ratio < 0.15 else (0, 100, 255)
                    cv2.circle(debug_img, (cx, cy), radius_est, colour, 2)
                    cv2.putText(debug_img, f"{q}.{opt}",
                                (cx - radius_est, cy - radius_est - 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 0, 0), 1, cv2.LINE_AA)

    if debug_out:
        cv2.imwrite(debug_out, debug_img)

    # --- Two-pass verification ---
    all_vals = [v for row in raw_intensities.values() for v in row.values()]
    # Upper quartile approximates the blank-bubble brightness
    blank_baseline = float(np.percentile(all_vals, 75))
    q15 = float(np.percentile(all_vals, 15))

    fill_threshold = blank_baseline * 0.82       # must be at least this dark
    absolute_dark  = min(q15 * 1.5, blank_baseline * 0.68)  # definitely filled

    _log(f"baseline={blank_baseline:.1f}  fill_thresh={fill_threshold:.1f}  "
         f"abs_dark={absolute_dark:.1f}")

    answers: Dict[int, Optional[int]] = {}
    flags: Dict[int, str] = {}
    confidence: Dict[int, float] = {}

    for q in sorted(raw_intensities):
        opts = raw_intensities[q]
        ranked = sorted(opts.items(), key=lambda x: x[1])
        darkest_opt, darkest_val = ranked[0]
        second_opt,  second_val  = ranked[1]
        brightest_val = ranked[3][1]

        darkest_fill = bubble_details[q][darkest_opt]['filled_ratio']
        second_fill  = bubble_details[q][second_opt]['filled_ratio']

        row_mean = float(np.mean([v for _, v in ranked]))
        row_std  = float(np.std([v for _, v in ranked]))
        gap      = second_val - darkest_val
        rel_gap  = gap / (row_mean + 1e-9)

        # Pass 1 — intensity evidence
        p1_obvious  = darkest_val < absolute_dark
        p1_relative = rel_gap > 0.10 and gap > 4
        p1_below    = darkest_val < fill_threshold
        pass1 = p1_obvious or (p1_below and p1_relative)

        # Pass 2 — filled-pixel evidence
        p2_filled   = darkest_fill > 0.15
        p2_distinct = darkest_fill > second_fill * 1.4
        pass2 = p2_filled and p2_distinct

        # Both must agree OR one is very strong
        is_filled = (pass1 and pass2) or p1_obvious or (p2_filled and p1_below)

        if is_filled:
            darkness_score = max(0.0, 1.0 - darkest_val / (blank_baseline + 1e-9))
            gap_score      = min(1.0, rel_gap / 0.20)
            fill_score     = min(1.0, darkest_fill / 0.30)
            conf = int(min(100, darkness_score * 45 + gap_score * 35 + fill_score * 20))

            answers[q]    = darkest_opt
            confidence[q] = float(conf)

            second_also_dark = (second_val < fill_threshold * 0.92
                                and second_fill > 0.15
                                and rel_gap < 0.07)
            if second_also_dark:
                flags[q] = "multi_mark"
                confidence[q] = float(max(25, conf - 30))
                _log(f"Q{q}: multi_mark (opts {darkest_opt} & {second_opt})")
            elif conf < 40:
                flags[q] = "low_confidence"
                _log(f"Q{q}: low_confidence ({conf}%)")
        else:
            answers[q]    = None
            confidence[q] = 0.0

            all_similar = row_std < 4
            all_dark    = brightest_val < fill_threshold * 0.88
            all_filled  = all(bubble_details[q][o]['filled_ratio'] > 0.18
                              for o in range(1, 5))
            if (all_dark and all_similar) or all_filled:
                flags[q] = "row_smudged"
                _log(f"Q{q}: row_smudged")
            else:
                flags[q] = "no_clear_mark"
                _log(f"Q{q}: no_clear_mark")

    return answers, flags, raw_intensities, confidence


# ---------------------------------------------------------------------------
# Scoring & batch utilities
# ---------------------------------------------------------------------------

def score_sheet(
    answers: Dict[int, Optional[int]],
    answer_key: Dict[int, int],
) -> Tuple[int, Dict[int, bool]]:
    """Compare answers to the answer key. Returns (score, {q: is_correct})."""
    correct: Dict[int, bool] = {}
    score = 0
    for q, key_opt in answer_key.items():
        ok = answers.get(q) == key_opt
        correct[q] = ok
        if ok:
            score += 1
    return score, correct


def batch_to_excel(
    image_paths: List[str],
    out_xlsx: str,
    answer_key: Optional[Dict[int, int]] = None,
    roll_numbers: Optional[List[str]] = None,
) -> None:
    """Generate an Excel report with colour-coded confidence indicators."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "OMR Results"

    header = ["Sheet #", "Roll No"] + [f"Q{i}" for i in range(1, 41)]
    header += (["Score", "Flagged", "Avg Confidence"] if answer_key
                else ["Flagged", "Avg Confidence"])
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    fill_yellow = PatternFill("solid", start_color="FFFF00")
    fill_orange = PatternFill("solid", start_color="FFA500")
    fill_red    = PatternFill("solid", start_color="FF6B6B")

    for idx, path in enumerate(image_paths, start=1):
        roll = (roll_numbers[idx - 1] if roll_numbers and idx <= len(roll_numbers) else "")
        try:
            ans, flg, _, conf = detect_bubbles(path)
            row = [idx, roll] + [ans.get(q, "") for q in range(1, 41)]
            avg_conf = int(np.mean([conf.get(q, 0) for q in range(1, 41)]))
            if answer_key:
                sc, _ = score_sheet(ans, answer_key)
                row += [sc, ", ".join(f"Q{q}" for q in sorted(flg)), avg_conf]
            else:
                row += [", ".join(f"Q{q}" for q in sorted(flg)), avg_conf]
            ws.append(row)
            rn = ws.max_row
            for q, ftype in flg.items():
                col = 2 + q
                if ftype == "multi_mark":
                    ws.cell(row=rn, column=col).fill = fill_orange
                elif ftype == "low_confidence":
                    ws.cell(row=rn, column=col).fill = fill_yellow
                elif ftype in ("no_clear_mark", "row_smudged"):
                    ws.cell(row=rn, column=col).fill = fill_red
        except Exception as exc:
            row = [idx, roll] + ["ERROR"] * 40
            row += ([0, str(exc), 0] if answer_key else [str(exc), 0])
            ws.append(row)

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 10
    wb.save(out_xlsx)


def print_answers(answers: Dict[int, Optional[int]], total_questions: int = 40) -> None:
    for q in range(1, total_questions + 1):
        opt = answers.get(q)
        print(f"Q{q}: {'Option ' + str(opt) if opt else 'Not marked'}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        _out = sys.argv[2]
        _imgs = sys.argv[3:]
        batch_to_excel(_imgs, _out)
        print(f"Saved results for {len(_imgs)} sheet(s) to {_out}")
    else:
        _path = sys.argv[1] if len(sys.argv) > 1 else None
        if not _path:
            print("Usage: python omr_scanner.py <image> [debug_out.jpg]")
            sys.exit(1)
        _debug = sys.argv[2] if len(sys.argv) > 2 else None
        _ans, _flg, _, _conf = detect_bubbles(_path, _debug)
        print_answers(_ans)
        if _flg:
            print(f"\nFlags: {', '.join(f'Q{q}={v}' for q, v in sorted(_flg.items()))}")
        print(f"Avg confidence: {int(np.mean([_conf.get(q, 0) for q in range(1, 41)]))}%")
