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
"""
import cv2
import numpy as np

CANON_W = 1400
CANON_H = 2200


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


def find_outer_border(img):
    """
    Locate the outer rectangle of the answer-grid table (or, failing that,
    the whole sheet) and return its 4 ordered corners in ORIGINAL image
    pixel coordinates.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Adaptive threshold copes with uneven phone-camera lighting far
    # better than a single global threshold.
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 35, 15
    )
    thresh = cv2.dilate(thresh, np.ones((5, 5), np.uint8), iterations=2)

    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise RuntimeError("No contours found - cannot locate sheet border.")

    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    img_area = img.shape[0] * img.shape[1]
    for c in contours[:15]:
        area = cv2.contourArea(c)
        if area < 0.15 * img_area:
            # Too small to be the table/sheet outline; contours are
            # sorted by area so nothing further down will qualify either.
            break
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            return _order_corners(approx)

    # Fallback: use the minAreaRect of the single largest contour, which
    # handles slightly bowed/rounded table borders that approxPolyDP
    # fails to collapse to exactly 4 points.
    largest = contours[0]
    rect = cv2.minAreaRect(largest)
    box = cv2.boxPoints(rect)
    return _order_corners(box.reshape(4, 1, 2).astype("float32"))


def align_sheet(img, out_size=(CANON_W, CANON_H), debug_path=None):
    """
    Warp `img` (BGR np.ndarray) into the canonical frame.
    Returns the warped BGR image of size out_size.
    """
    corners = find_outer_border(img)
    w, h = out_size
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(corners, dst)
    warped = cv2.warpPerspective(img, M, (w, h))

    if debug_path:
        dbg = img.copy()
        cv2.polylines(dbg, [corners.astype(int)], True, (0, 0, 255), 6)
        cv2.imwrite(debug_path, dbg)

    return warped


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "reference_sheet.jpg"
    img = cv2.imread(src)
    warped = align_sheet(img, debug_path="debug_border_detected.jpg")
    cv2.imwrite("debug_warped.jpg", warped)
    print("Wrote debug_border_detected.jpg and debug_warped.jpg")
