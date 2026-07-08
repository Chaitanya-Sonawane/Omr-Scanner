import cv2
import numpy as np
import json
import sys


def _try_hough(gray_blur, min_r, max_r, param2):
    circles = cv2.HoughCircles(
        gray_blur, cv2.HOUGH_GRADIENT, dp=1, minDist=18,
        param1=50, param2=param2, minRadius=min_r, maxRadius=max_r
    )
    return circles


def _detect_circles(gray):
    h, w = gray.shape
    r_est = max(8, min(30, w // 80))
    min_r = max(6, r_est - 6)
    max_r = r_est + 10
    blur = cv2.medianBlur(gray, 5)
    for param2 in [22, 18, 14, 10]:
        circles = _try_hough(blur, min_r, max_r, param2)
        if circles is not None and len(circles[0]) >= 8:
            return circles, blur
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    blur2 = cv2.medianBlur(enhanced, 5)
    for param2 in [18, 12]:
        circles = _try_hough(blur2, min_r, max_r, param2)
        if circles is not None and len(circles[0]) >= 8:
            return circles, blur2
    return None, blur


def _safe_kmeans(data, k, criteria, attempts=10):
    n = len(data)
    if n < k:
        return None, None
    _, labels, centers = cv2.kmeans(data, k, None, criteria, attempts, cv2.KMEANS_PP_CENTERS)
    return labels, centers


def _compute_row_y(all_pts):
    """
    Compute the 20 shared row y-positions from ALL detected bubble points
    on the sheet (both option blocks pooled together). Both blocks sit on
    the exact same printed horizontal lines, so pooling roughly doubles
    the points feeding each row's cluster (up to 8 per row instead of 4),
    which makes row positions far less likely to be thrown off by a
    single missing/extra detection in just one block.
    """
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    all_ys = all_pts[:, 1].reshape(-1, 1).astype(np.float32)
    n_rows_k = min(20, len(all_ys))
    row_labels, row_centers = _safe_kmeans(all_ys, n_rows_k, criteria)

    if row_labels is None:
        y_min, y_max = float(all_ys.min()), float(all_ys.max())
        row_y_sorted = np.linspace(y_min, y_max, 20).tolist()
    else:
        cluster_y = sorted(float(c) for c in row_centers.flatten())
        if len(cluster_y) < 20:
            diffs = np.diff(cluster_y)
            diffs = diffs[diffs > 3]
            pitch = float(np.median(diffs)) if len(diffs) else 30.0
            row_y_sorted = list(cluster_y)
            while len(row_y_sorted) < 20:
                row_y_sorted.append(row_y_sorted[-1] + pitch)
        else:
            row_y_sorted = cluster_y

    # Row positions should increase ~linearly (constant pitch, plus mild
    # tilt/perspective). KMeans occasionally misplaces an edge row (too few
    # points assigned to it); fit a line through all 20 rows and snap any
    # row whose position deviates too far from the fitted trend back onto it.
    row_idx_arr = np.arange(20)
    row_y_arr = np.array(row_y_sorted, dtype=np.float64)
    diffs = np.diff(row_y_arr)
    diffs = diffs[diffs > 3]
    est_pitch = float(np.median(diffs)) if len(diffs) else 30.0
    for _ in range(2):
        ay, by_ = np.polyfit(row_idx_arr, row_y_arr, 1)
        fitted = ay * row_idx_arr + by_
        resid = row_y_arr - fitted
        bad = np.abs(resid) > max(est_pitch * 0.4, 8)
        if not bad.any():
            break
        row_y_arr[bad] = fitted[bad]
    return row_y_arr.tolist()


def _col_centers_from_projection(gray, x_min, x_max, y_min, y_max, n_cols=4):
    """
    Find n_cols bubble-column x-centers within the answer grid region
    [x_min:x_max, y_min:y_max] using a vertical dark-pixel projection.

    We look at ONLY the answer grid rows (not borders/headers) and find
    the n_cols peaks that correspond to bubble columns. Bubbles are circular
    dark marks — heavily filled ones are darker, giving a stronger signal.
    Grid lines are thin and contribute less than a full column of circles.
    """
    region = gray[y_min:y_max, x_min:x_max]
    # threshold: pixels darker than 100 (bubbles + lines)
    dark = (region < 100).astype(float)
    proj = np.sum(dark, axis=0)

    # smooth with a bubble-width kernel to merge each bubble into one peak
    bw = max(5, (x_max - x_min) // (n_cols * 4))
    kernel = np.ones(bw) / bw
    proj_smooth = np.convolve(proj, kernel, mode='same')

    region_h = y_max - y_min
    min_height = region_h * 0.10   # column must have dark pixels in >10% of rows
    min_dist = max(20, (x_max - x_min) // (n_cols * 2))

    from scipy.signal import find_peaks
    peaks, _ = find_peaks(proj_smooth, height=min_height, distance=min_dist)

    if len(peaks) < n_cols:
        peaks, _ = find_peaks(proj_smooth, height=region_h * 0.04, distance=min_dist // 2)

    if len(peaks) < n_cols:
        return None

    # pick the n_cols strongest
    peak_vals = [(int(peaks[i]), float(proj_smooth[peaks[i]])) for i in range(len(peaks))]
    peak_vals.sort(key=lambda x: -x[1])
    top = sorted([p + x_min for p, v in peak_vals[:n_cols]])

    # enforce uniform spacing
    pitch = float(np.median(np.diff(top)))
    x0 = float(np.mean([top[i] - i * pitch for i in range(n_cols)]))
    return [x0 + i * pitch for i in range(n_cols)]


def _build_grid(block_pts, gray, radius_est, row_y_sorted):
    """
    Build a 20x4 grid of (x,y) sample positions for one answer block.

    Column x-positions are found via vertical dark-pixel projection over
    the answer grid region — robust to heavily-filled bubbles because filled
    bubbles are darker (stronger signal), not lighter. Falls back to
    Hough-based kmeans with uniform refit if projection fails.
    """
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    h, w = gray.shape

    # x/y bounds of this block's answer grid
    x_min = max(0, int(block_pts[:, 0].min()) - radius_est * 2)
    x_max = min(w, int(block_pts[:, 0].max()) + radius_est * 2)
    y_min = max(0, int(np.min([row_y_sorted[0]])) - radius_est * 2)
    y_max = min(h, int(np.max([row_y_sorted[-1]])) + radius_est * 2)

    # ── primary: projection-based column detection ────────────────────────────
    col_x_fitted = _col_centers_from_projection(gray, x_min, x_max, y_min, y_max, n_cols=4)

    if col_x_fitted is not None:
        col_x_center = {i: col_x_fitted[i] for i in range(4)}
    else:
        # ── fallback: kmeans on Hough circles + uniform refit ─────────────────
        n_cols = min(4, len(block_pts))
        bxs = block_pts[:, 0].reshape(-1, 1).astype(np.float32)
        col_labels, col_centers = _safe_kmeans(bxs, n_cols, criteria)
        if col_labels is None or n_cols < 4:
            raw_sorted = np.linspace(float(bxs.min()), float(bxs.max()), 4).tolist()
        else:
            col_centers_list = sorted(col_centers.flatten().tolist())
            cluster_order = np.argsort(col_centers.flatten())
            cluster_to_opt = {int(cluster_order[i]): i for i in range(len(cluster_order))}
            col_pts_by_opt = {opt_idx: [] for opt_idx in range(4)}
            for i in range(len(block_pts)):
                opt_idx = cluster_to_opt.get(int(col_labels[i][0]), -1)
                if 0 <= opt_idx < 4:
                    col_pts_by_opt[opt_idx].append(block_pts[i])
            raw_sorted = []
            for opt_idx in range(4):
                pts = col_pts_by_opt[opt_idx]
                raw_sorted.append(
                    float(np.median([p[0] for p in pts]))
                    if pts else col_centers_list[opt_idx]
                )
            raw_sorted = sorted(raw_sorted)
        pitch = float(np.median(np.diff(raw_sorted)))
        x0 = float(np.mean([raw_sorted[i] - i * pitch for i in range(4)]))
        col_x_center = {i: x0 + i * pitch for i in range(4)}

    # ── build final grid ──────────────────────────────────────────────────────
    col_grid = {}
    for opt_idx in range(4):
        cx = col_x_center[opt_idx]
        grid_col = []
        for row_idx in range(20):
            gx = int(round(cx))
            gy = int(round(row_y_sorted[row_idx]))
            gx = max(radius_est, min(w - radius_est - 1, gx))
            gy = max(radius_est, min(h - radius_est - 1, gy))
            grid_col.append((gx, gy))
        col_grid[opt_idx] = grid_col

    return col_grid


def detect_bubbles(img_path, debug_out=None):
    img = cv2.imread(img_path)
    if img is None:
        raise RuntimeError(f"Could not read image: {img_path}")
    orig = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    raw_circles, gray_blur = _detect_circles(gray)
    if raw_circles is None:
        raise RuntimeError(
            f"No circles found in {img_path}. "
            "Check that the image shows a clear OMR sheet with visible bubbles."
        )
    circles = np.round(raw_circles[0]).astype(int)

    circles = [c for c in circles if 50 < c[0] < w - 50 and 200 < c[1] < h - 30]
    if len(circles) < 8:
        raise RuntimeError(f"Too few circles detected ({len(circles)}) after filtering edges.")

    # filter to circles near median radius (removes text/border/stamp noise)
    radii = np.array([c[2] for c in circles])
    r_med = np.median(radii)
    circles = [c for c in circles if abs(c[2] - r_med) <= max(2, r_med * 0.35)]
    if len(circles) < 8:
        raise RuntimeError(f"Too few circles remain ({len(circles)}) after radius filtering.")

    # drop stray outliers above the answer grid (e.g. the circular
    # institution logo/stamp printed in the header, which can match the
    # expected bubble radius). Header debris is always a small cluster near
    # the very top of the sheet, so scan a generous early window (not just
    # the first ~15 points, which can miss a larger debris cluster) and cut
    # at the single largest gap found there. Picking the largest gap (rather
    # than aiming for an exact expected count) avoids over-trimming real
    # grid rows when the total circle count is naturally off from 160.
    ys_all = sorted(c[1] for c in circles)
    n_total = len(ys_all)
    window = min(50, n_total)
    cut_y = None
    best_gap = 0
    for i in range(1, window):
        gap = ys_all[i] - ys_all[i - 1]
        if gap > 60 and gap > best_gap:
            best_gap = gap
            cut_y = ys_all[i]
    if cut_y is not None:
        circles = [c for c in circles if c[1] >= cut_y]
    if len(circles) < 8:
        raise RuntimeError(f"Too few circles remain ({len(circles)}) after outlier removal.")

    pts = np.array([[c[0], c[1]] for c in circles])
    radius_est = int(np.median([c[2] for c in circles]))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)

    xs = pts[:, 0].reshape(-1, 1).astype(np.float32)
    block_labels, block_centers = _safe_kmeans(xs, 2, criteria)
    if block_labels is None:
        block_labels = np.zeros((len(pts), 1), dtype=np.int32)
        block_centers = np.array([[xs.mean()], [xs.mean()]], dtype=np.float32)

    left_block_id = int(np.argmin(block_centers.flatten()))

    results = {}
    debug_img = orig.copy()
    # Sample only the inner ~55% of each bubble's radius. A tighter sample
    # area is less likely to pick up ink bleeding in from an adjacent row
    # or column when the grid position is off by a few pixels.
    sample_r = max(int(radius_est * 0.55), 6)

    for block_id, q_offset in [(left_block_id, 0), (1 - left_block_id, 20)]:
        mask = block_labels.flatten() == block_id
        block_pts = pts[mask]

        if len(block_pts) < 4:
            for row_idx in range(20):
                results[row_idx + 1 + q_offset] = {1: 255, 2: 255, 3: 255, 4: 255}
            continue

        row_y_sorted = _compute_row_y(block_pts)
        col_grid = _build_grid(block_pts, gray, radius_est, row_y_sorted)

        for row_idx in range(20):
            q_num = row_idx + 1 + q_offset
            row_vals = {}
            for opt_idx in range(4):
                x, y = col_grid[opt_idx][row_idx]
                mask_c = np.zeros(gray.shape, dtype=np.uint8)
                cv2.circle(mask_c, (x, y), sample_r, 255, -1)
                mean_val = cv2.mean(gray, mask=mask_c)[0]
                row_vals[opt_idx + 1] = mean_val
                cv2.circle(debug_img, (x, y), radius_est, (0, 255, 0), 2)
                cv2.circle(debug_img, (x, y), 2, (0, 0, 255), -1)
                # Label with "question.option" so the sampled x/y position can be
                # visually cross-checked against the printed "1 2 3 4" columns.
                label = f"{q_num}.{opt_idx + 1}"
                cv2.putText(debug_img, label, (x - radius_est, y - radius_est - 3),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 0, 0), 1, cv2.LINE_AA)
            results[q_num] = row_vals

    if debug_out:
        cv2.imwrite(debug_out, debug_img)

    # ---- adaptive blank baseline with consistent thresholding ----
    # Most of the 160 sampled bubbles are unmarked, so the median brightness
    # is a reliable blank baseline. Filled bubbles (especially heavily darkened
    # pen marks) are significantly darker.
    all_vals = [v for opts in results.values() for v in opts.values()]
    blank_baseline = float(np.median(all_vals))
    # 0.75 requires a clearly filled bubble — stricter than before to avoid
    # wrinkles/shadows on crumpled sheets being mistaken for marks.
    fill_threshold = blank_baseline * 0.75

    answers = {}
    flags = {}
    for q in sorted(results.keys()):
        opts = results[q]
        sorted_opts = sorted(opts.items(), key=lambda x: x[1])
        darkest_opt, darkest_val = sorted_opts[0]
        second_opt, second_val = sorted_opts[1]
        gap = second_val - darkest_val

        if darkest_val < fill_threshold:
            # Check for multi-mark (two or more darkened bubbles)
            if second_val < fill_threshold and gap < blank_baseline * 0.12:
                flags[q] = "multi_mark"
                answers[q] = None
            else:
                answers[q] = darkest_opt
                if gap < blank_baseline * 0.15:
                    flags[q] = "low_confidence"
        else:
            # Nothing crossed the threshold but still mark the darkest bubble
            answers[q] = darkest_opt
            flags[q] = "low_confidence"

    return answers, flags, results


def score_sheet(answers, answer_key):
    correct = {}
    score = 0
    for q, key_opt in answer_key.items():
        marked = answers.get(q)
        is_correct = marked == key_opt
        correct[q] = is_correct
        if is_correct:
            score += 1
    return score, correct


def batch_to_excel(image_paths, out_xlsx, answer_key=None, roll_numbers=None):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "OMR Results"

    header = ["Sheet #", "Roll No"] + [f"Q{i}" for i in range(1, 41)]
    if answer_key:
        header += ["Score", "Flagged (low confidence)"]
    else:
        header += ["Flagged (low confidence)"]
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    yellow = PatternFill("solid", start_color="FFFF00")

    for idx, path in enumerate(image_paths, start=1):
        answers, flags, _ = detect_bubbles(path)
        roll = roll_numbers[idx - 1] if roll_numbers else ""
        row = [idx, roll] + [answers.get(q, "") for q in range(1, 41)]
        if answer_key:
            score, _ = score_sheet(answers, answer_key)
            row += [score, ", ".join(f"Q{q}" for q in sorted(flags))]
        else:
            row += [", ".join(f"Q{q}" for q in sorted(flags))]
        ws.append(row)

        row_num = ws.max_row
        for q in flags:
            col_idx = 2 + q
            ws.cell(row=row_num, column=col_idx).fill = yellow

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 10

    wb.save(out_xlsx)


def print_simple_answers(answers, total_questions=40):
    """Print just 'Q{N}: Option X' for every question, one per line.
    Unmarked questions print as 'Not marked'."""
    for q in range(1, total_questions + 1):
        opt = answers.get(q)
        if opt is None:
            print(f"Q{q}: Not marked")
        else:
            print(f"Q{q}: {opt}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        out_xlsx = sys.argv[2]
        images = sys.argv[3:]
        batch_to_excel(images, out_xlsx)
        print(f"Saved results for {len(images)} sheet(s) to {out_xlsx}")
    else:
        img_path = sys.argv[1]
        debug_out = sys.argv[2] if len(sys.argv) > 2 else None
        answers, flags, raw = detect_bubbles(img_path, debug_out)
        print_simple_answers(answers)
