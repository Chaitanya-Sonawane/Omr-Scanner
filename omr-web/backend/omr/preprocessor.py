"""
Image pre-processing: deskew, perspective correction, adaptive threshold.
Returns a normalized grayscale image at TARGET_W x TARGET_H.

Handles phone-camera photos of OMR sheets:
- Tries perspective warp using the largest rectangular contour (the answer table)
- Falls back gracefully to a simple resize if no clean rectangle is found
- Applies CLAHE to improve local contrast for pen-filled bubbles
"""
import cv2
import numpy as np

TARGET_W = 800
TARGET_H = 1040


class ProcessingError(Exception):
    pass


def load_image(path: str) -> np.ndarray:
    """Load image from path; handle PDF via PyMuPDF if needed."""
    ext = path.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ProcessingError("PyMuPDF not installed; cannot process PDF files.")
        doc = fitz.open(path)
        page = doc.load_page(0)
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
        return arr
    else:
        # Try reading as color first, then convert to grayscale
        # This handles more image formats properly
        img = cv2.imread(path)
        if img is None:
            raise ProcessingError(f"Cannot read image file: {path}")
        
        # Convert to grayscale if color
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        if img is None or img.size == 0:
            raise ProcessingError(f"Loaded image is empty: {path}")
            
        return img


def _auto_canny(image: np.ndarray, sigma: float = 0.33) -> np.ndarray:
    median = np.median(image)
    lower = int(max(0, (1.0 - sigma) * median))
    upper = int(min(255, (1.0 + sigma) * median))
    return cv2.Canny(image, lower, upper)


def _angle(p1, p2, p0) -> float:
    dx1, dy1 = float(p1[0] - p0[0]), float(p1[1] - p0[1])
    dx2, dy2 = float(p2[0] - p0[0]), float(p2[1] - p0[1])
    return (dx1 * dx2 + dy1 * dy2) / (
        np.sqrt((dx1**2 + dy1**2) * (dx2**2 + dy2**2)) + 1e-10
    )


def _is_valid_rect(approx) -> bool:
    if len(approx) != 4:
        return False
    pts = approx.reshape(4, 2)
    for i in range(2, 5):
        cos = abs(_angle(pts[i % 4], pts[i - 2], pts[i - 1]))
        if cos >= 0.3:
            return False
    return True


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    rect = _order_points(pts)
    tl, tr, br, bl = rect
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxW = int(max(widthA, widthB))
    maxH = int(max(heightA, heightB))
    dst = np.array([[0, 0], [maxW - 1, 0], [maxW - 1, maxH - 1], [0, maxH - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (maxW, maxH))


def find_page(image: np.ndarray) -> np.ndarray:
    """
    Find the answer table boundary using contour detection.
    For phone photos the sheet border may not be visible, so we require
    the contour to cover at least 25% of the image area to be a real page rect.
    """
    h, w = image.shape[:2]
    min_area = h * w * 0.25  # must cover ≥25% of frame

    blurred = cv2.GaussianBlur(image, (5, 5), 0)
    blurred = cv2.normalize(blurred, None, 0, 255, cv2.NORM_MINMAX)
    edged = _auto_canny(blurred)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
    closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for cnt in contours[:5]:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        area = cv2.contourArea(approx)
        if _is_valid_rect(approx) and area > min_area:
            return approx.reshape(4, 2).astype("float32")
    return None


def _apply_clahe(img: np.ndarray) -> np.ndarray:
    """Enhance local contrast so pen-filled bubbles stand out clearly."""
    img_u8 = np.clip(img, 0, 255).astype(np.uint8)
    # Increased clipLimit from 2.0 to 3.0 for better bubble contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(img_u8)
    return enhanced.astype(np.float32)


def preprocess(path: str) -> np.ndarray:
    """
    Full pipeline: load → resize → CLAHE → normalize.
    Perspective warp is intentionally skipped — it can mis-order corners
    and swap left/right columns, causing wrong option detection.
    Returns float32 grayscale image [0,255] at TARGET_W x TARGET_H.
    """
    img = load_image(path)
    
    if img is None or img.size == 0:
        raise ProcessingError(f"Failed to load image from {path}")

    # Resize to fixed processing dimensions (NO perspective warp)
    img = cv2.resize(img, (TARGET_W, TARGET_H), interpolation=cv2.INTER_AREA)
    
    if img is None or img.size == 0:
        raise ProcessingError("Image became empty after resize")

    # CLAHE: improves contrast for pen-filled bubbles on phone-camera photos
    img = _apply_clahe(img)

    # Final normalization
    if img.max() > img.min():
        img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)

    return img.astype(np.float32)
