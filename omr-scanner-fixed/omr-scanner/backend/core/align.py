"""
align.py
--------
Aligns any photographed OMR sheet into a fixed canonical pixel space by
detecting the outer border of the answer grid and applying a perspective
warp (cv2.warpPerspective). This is the ONLY per-sheet geometry step -
after this, every sheet lives in identical pixel coordinates, so the
160-bubble template (built once in calibrate_template.py) can be reused
unchanged for every scan.

Canonical space is fixed at CANON_W x CANON_H. The template JSON is
defined in this same space.

Hardening added on top of the original architecture (no redesign):
  - EXIF-aware image loading (phone photos are frequently rotated only in
    EXIF metadata; cv2.imread ignores this and silently reads them sideways).
  - Blur (focus) quality scoring so an out-of-focus photo can be flagged
    instead of silently producing garbage bubble reads.
  - Multi-strategy border detection (adaptive-threshold contour ->
    Canny-edge contour -> minAreaRect -> full-frame fallback), each
    validated for plausible geometry (convexity, corner angles) before
    being accepted.
  - Detection is run on a downscaled working copy for speed/robustness,
    then the corners are rescaled back to full resolution so the actual
    perspective warp is done against full-resolution pixels.
  - Content-based 180 degree orientation correction, since a sheet fed in
    upside-down still yields a perfectly valid rectangle - only the pixel
    content reveals it is flipped.
  - Every alignment reports a structured quality dict so downstream code
    (scan_omr.py) can decide to trust or flag a sheet, rather than
    guessing silently.
"""
import cv2
import numpy as np
from PIL import Image, ImageOps

CANON_W = 1400
CANON_H = 2200

# Quality thresholds (tuned to be conservative: prefer flagging REVIEW over
# a confident wrong answer).
BLUR_VAR_MIN = 60.0          # Laplacian-variance floor for "in focus enough"
DETECT_MAX_DIM = 1600.0      # working resolution for contour search
MIN_BORDER_AREA_FRAC = 0.15  # border contour must cover >=15% of frame
CORNER_ANGLE_TOL_DEG = 25    # tolerated deviation from 90 degrees per corner


def load_image(path):
    """
    EXIF-aware image load. Returns a BGR np.ndarray exactly as it should be
    viewed (i.e. phone-camera rotation metadata is honoured), unlike a bare
    cv2.imread which ignores EXIF orientation and can hand back a sideways
    or upside-down frame.
    """
    with Image.open(path) as pil_img:
        pil_img = ImageOps.exif_transpose(pil_img)  # honour EXIF rotation
        pil_img = pil_img.convert("RGB")
        rgb = np.array(pil_img)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def blur_score(gray):
    """Laplacian variance: low value == likely out of focus / motion blur."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _order_corners(pts):
    """Order 4 points as top-left, top-right, bottom-right, bottom-left."""
    pts = pts.reshape(4, 2).astype("float32")
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).flatten()
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return np.array([tl, tr, br, bl], dtype="float32")


def _corner_angles_ok(corners, tol_deg=CORNER_ANGLE_TOL_DEG):
    """Reject wildly non-rectangular quadrilaterals (bad detections)."""
    pts = corners
    ok = True
    for i in range(4):
        a = pts[(i - 1) % 4]
        b = pts[i]
        c = pts[(i + 1) % 4]
        v1 = a - b
        v2 = c - b
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 < 1e-3 or n2 < 1e-3:
            return False
        cos_a = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
        ang = np.degrees(np.arccos(cos_a))
        if abs(ang - 90.0) > tol_deg:
            ok = False
    return ok


MAX_BORDER_AREA_FRAC = 0.90  # reject a candidate that's essentially the whole frame
TARGET_ASPECT = CANON_W / CANON_H  # width/height of the table we expect to find


def _quad_aspect(corners):
    tl, tr, br, bl = corners
    top_w = np.linalg.norm(tr - tl)
    bot_w = np.linalg.norm(br - bl)
    left_h = np.linalg.norm(bl - tl)
    right_h = np.linalg.norm(br - tr)
    w = (top_w + bot_w) / 2.0
    h = (left_h + right_h) / 2.0
    return w / max(h, 1e-6)


def _candidate_from_contours(thresh, img_area, min_area_frac=MIN_BORDER_AREA_FRAC):
    """
    Collects every plausible quadrilateral (both clean 4-point contour
    approximations and minAreaRect fits of larger blobs), then - rather
    than blindly trusting whichever is largest - scores each by how close
    its aspect ratio is to the expected table shape. On real photos the
    largest dark contour is frequently the whole page or a shadow blob
    (not the inner table border), so area alone is an unreliable signal;
    aspect-ratio plausibility catches this without needing a fixed size.
    """
    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    candidates = []  # (aspect_error, -area, ordered_corners, method)
    for c in contours[:25]:
        area = cv2.contourArea(c)
        frac = area / img_area
        if frac < min_area_frac:
            break
        if frac > MAX_BORDER_AREA_FRAC:
            continue  # almost certainly the page/background, not the table

        found_clean_quad = False
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            ordered = _order_corners(approx)
            if _corner_angles_ok(ordered):
                aspect_err = abs(_quad_aspect(ordered) - TARGET_ASPECT)
                candidates.append((aspect_err, -area, ordered, "contour_4pt"))
                found_clean_quad = True

        # A real table border can fail the direct check above if an
        # internal divider line meets the border (a T-junction adds
        # extra vertices / breaks convexity). Taking the convex hull
        # first strips exactly that kind of small inward notch while
        # preserving the true outer corners.
        if not found_clean_quad:
            hull = cv2.convexHull(c)
            hull_peri = cv2.arcLength(hull, True)
            hull_approx = cv2.approxPolyDP(hull, 0.02 * hull_peri, True)
            if len(hull_approx) == 4 and cv2.isContourConvex(hull_approx):
                ordered = _order_corners(hull_approx)
                if _corner_angles_ok(ordered):
                    aspect_err = abs(_quad_aspect(ordered) - TARGET_ASPECT)
                    candidates.append((aspect_err, -area, ordered, "contour_4pt_hull"))
                    found_clean_quad = True

        if found_clean_quad:
            continue

        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect)
        ordered = _order_corners(box.reshape(4, 1, 2).astype("float32"))
        if _corner_angles_ok(ordered, tol_deg=40):
            aspect_err = abs(_quad_aspect(ordered) - TARGET_ASPECT)
            # minAreaRect candidates are the least targeted fallback (they
            # can be inflated by a single stray notch/protrusion), so rank
            # them slightly worse than an equally-plausible clean quad.
            candidates.append((aspect_err + 0.08, -area, ordered, "min_area_rect"))

    if not candidates:
        return None
    candidates.sort(key=lambda t: (t[0], t[1]))
    _, _, ordered, method = candidates[0]
    return ordered, method


def _refine_corners_subpixel(gray_full, corners, search_radius):
    """
    The initial border is found on a downscaled image, which caps its
    precision to roughly 1/scale full-resolution pixels. That error can be
    large enough to introduce a small but systematic shear/scale error in
    the perspective warp (subtly misplacing all 160 bubble coordinates,
    worse the further a bubble is from the top-left anchor). cornerSubPix
    pulls each corner to the true sub-pixel gradient corner on the FULL
    resolution image, which materially improves downstream bubble-center
    accuracy at negligible cost.

    Falls back to the un-refined corner (per-corner) if the refinement
    jumps further than `search_radius` - i.e. if there was no clean corner
    feature nearby, we don't trust the "refinement".
    """
    win = int(np.clip(search_radius, 8, 40))
    pts = corners.reshape(-1, 1, 2).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.001)
    try:
        refined = cv2.cornerSubPix(gray_full, pts.copy(), (win, win), (-1, -1), crit)
    except cv2.error:
        return corners
    refined = refined.reshape(-1, 2)
    out = corners.copy()
    for i in range(4):
        shift = np.linalg.norm(refined[i] - corners[i])
        if shift <= search_radius * 1.5:
            out[i] = refined[i]
    if _corner_angles_ok(out, tol_deg=35):
        return out.astype("float32")
    return corners


def find_outer_border(img):
    """
    Locate the outer rectangle of the answer-grid table (or, failing that,
    the whole sheet) and return (corners_in_original_coords, method, scale).

    Runs detection on a downscaled copy for speed and noise-robustness,
    then rescales corners back to full-resolution coordinates so the
    perspective warp uses full-quality pixels, then refines them with
    sub-pixel corner snapping on the full-resolution image.
    """
    h, w = img.shape[:2]
    scale = min(1.0, DETECT_MAX_DIM / max(h, w))
    small = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA) if scale < 1.0 else img

    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    img_area = small.shape[0] * small.shape[1]

    # Strategy 1: adaptive threshold (robust to uneven phone-camera lighting)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 35, 15
    )
    thresh = cv2.dilate(thresh, np.ones((5, 5), np.uint8), iterations=2)
    result = _candidate_from_contours(thresh, img_area)

    # Strategy 2: Canny edges, for cases where adaptive-threshold merges the
    # table into surrounding shadow/background.
    if result is None:
        edges = cv2.Canny(gray, 40, 120)
        edges = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=2)
        result = _candidate_from_contours(edges, img_area)

    if result is None:
        # Final fallback: treat the whole frame as the sheet. Always
        # succeeds so a single bad photo can't crash a batch job, but is
        # reported with "full_frame" so callers can flag low confidence.
        corners = np.array(
            [[0, 0], [small.shape[1] - 1, 0],
             [small.shape[1] - 1, small.shape[0] - 1], [0, small.shape[0] - 1]],
            dtype="float32",
        )
        method = "full_frame_fallback"
    else:
        corners, method = result

    if scale < 1.0:
        corners = corners / scale

    if method != "full_frame_fallback":
        gray_full = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        search_radius = (1.0 / scale) + 5 if scale < 1.0 else 10
        corners = _refine_corners_subpixel(gray_full, corners, search_radius)

    return corners.astype("float32"), method


def _orientation_flip_needed(warped_gray):
    """
    Content-based 180-degree check. A correctly-oriented printed answer
    sheet has its instructional header (dense text/ink) in the top band and
    a comparatively sparse margin at the very bottom. If the bottom band is
    reliably darker/denser than the top band, the sheet was fed upside-down
    even though the rectangle itself was detected correctly.
    """
    h = warped_gray.shape[0]
    band = max(10, int(h * 0.07))
    top = warped_gray[:band, :]
    bottom = warped_gray[-band:, :]
    top_ink = float(255 - top.mean())
    bottom_ink = float(255 - bottom.mean())
    # Require a clear margin, not just noise, before flipping.
    return bottom_ink > top_ink * 1.35 and bottom_ink > 12.0


def align_sheet(img, out_size=(CANON_W, CANON_H), debug_path=None, auto_orient=False):
    """
    Warp `img` (BGR np.ndarray) into the canonical frame.

    Returns (warped_bgr, quality) where quality is a dict with:
      - "border_method": how the border was found ("contour_4pt",
        "min_area_rect", or "full_frame_fallback")
      - "border_confidence": "high" / "medium" / "low"
      - "blur_score": Laplacian variance of the source image (higher=sharper)
      - "blur_ok": bool, whether blur_score clears BLUR_VAR_MIN
      - "orientation_flipped": bool, whether a 180-degree correction was applied

    `auto_orient` defaults to False: the header/footer ink-density heuristic
    used to detect an upside-down photo was validated against real scanned
    sheets and found to misfire on this form's layout (dense gridlines near
    the bottom out-weighing the thin header text). A wrong flip silently
    reverses every answer on the sheet, which is worse than the rare case
    of a genuinely upside-down photo - which a human would catch instantly
    from the debug overlay. Pass auto_orient=True only if you've verified
    the heuristic against your own sheet layout first.
    """
    src_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    b_score = blur_score(src_gray)

    corners, method = find_outer_border(img)
    w, h = out_size
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(corners, dst)
    warped = cv2.warpPerspective(img, M, (w, h))

    flipped = False
    if auto_orient:
        warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        if _orientation_flip_needed(warped_gray):
            warped = cv2.rotate(warped, cv2.ROTATE_180)
            flipped = True

    confidence = {
        "contour_4pt": "high",
        "contour_4pt_hull": "high",
        "min_area_rect": "medium",
        "full_frame_fallback": "low",
    }.get(method, "low")

    quality = {
        "border_method": method,
        "border_confidence": confidence,
        "blur_score": round(b_score, 1),
        "blur_ok": b_score >= BLUR_VAR_MIN,
        "orientation_flipped": flipped,
    }

    if debug_path:
        dbg = img.copy()
        cv2.polylines(dbg, [corners.astype(int)], True, (0, 0, 255), 6)
        cv2.imwrite(debug_path, dbg)

    return warped, quality


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "reference_sheet.jpg"
    img = load_image(src)
    warped, quality = align_sheet(img, debug_path="debug_border_detected.jpg")
    cv2.imwrite("debug_warped.jpg", warped)
    print("Wrote debug_border_detected.jpg and debug_warped.jpg")
    print("Quality:", quality)
