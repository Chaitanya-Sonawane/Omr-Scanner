"""
Image preprocessing pipeline for OMR sheets.

Provides a robust OpenCV-based pipeline that normalises contrast,
removes shadows, deskews the sheet, and sharpens edges — no heavy
ML dependencies required.

Usage:
    from enhancer import enhance_image, preprocess_for_omr

    # Save enhanced colour image to disk
    out_path = enhance_image("raw.jpg", "enhanced.jpg")

    # Get preprocessed grayscale ndarray ready for circle detection
    gray = preprocess_for_omr("raw.jpg")
"""

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _remove_shadow(gray: np.ndarray) -> np.ndarray:
    """Subtract morphological background to neutralise shadows and uneven lighting."""
    k = max(15, min(gray.shape[:2]) // 20 | 1)  # always odd, scales with image size
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    background = cv2.morphologyEx(gray, cv2.MORPH_DILATE, kernel)
    diff = cv2.absdiff(background, gray)
    return cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)


def _clahe(gray: np.ndarray, clip: float = 2.5) -> np.ndarray:
    return cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8)).apply(gray)


def _sharpen(gray: np.ndarray) -> np.ndarray:
    """Unsharp-mask sharpening — enhances bubble edges without amplifying noise."""
    blur = cv2.GaussianBlur(gray, (0, 0), sigmaX=2.0)
    return cv2.addWeighted(gray, 1.4, blur, -0.4, 0)


def _deskew(img: np.ndarray) -> np.ndarray:
    """Correct small rotation angles (<=10 deg) from dominant Hough line angle."""
    gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 40, 120, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold=80, minLineLength=max(50, img.shape[1] // 8), maxLineGap=20,
    )
    if lines is None or len(lines) < 5:
        return img

    angles = []
    for line in lines[:80]:
        x1, y1, x2, y2 = line[0]
        if x2 != x1:
            a = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if abs(a) <= 10:
                angles.append(a)

    if not angles:
        return img

    skew = float(np.median(angles))
    if abs(skew) < 0.3:
        return img

    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), skew, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def _enhance_opencv(img_bgr: np.ndarray) -> np.ndarray:
    """
    Full colour enhancement pipeline for OMR sheets:
      1. Deskew (correct small rotations)
      2. Shadow removal via morphological background subtraction on L channel
      3. CLAHE contrast normalisation
      4. Unsharp-mask sharpening
      5. Mild fast NLM denoising
    """
    img_bgr = _deskew(img_bgr)

    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)

    l_no_shadow = _remove_shadow(l_ch)
    l_eq = _clahe(l_no_shadow, clip=2.5)

    enhanced = cv2.cvtColor(cv2.merge([l_eq, a_ch, b_ch]), cv2.COLOR_LAB2BGR)

    # Per-channel sharpening preserves colour balance
    sharpened = cv2.merge([_sharpen(c) for c in cv2.split(enhanced)])

    # Light denoising — keep h small to avoid blurring bubble edges
    return cv2.fastNlMeansDenoisingColored(
        sharpened, None, h=4, hColor=4,
        templateWindowSize=7, searchWindowSize=21,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def preprocess_for_omr(input_path: str) -> np.ndarray:
    """
    Load an image, enhance it, and return a preprocessed grayscale ndarray
    ready for Hough circle detection.

    Pipeline: _enhance_opencv -> grayscale -> CLAHE -> median blur

    Returns:
        np.ndarray: uint8 grayscale image
    """
    img = cv2.imread(input_path)
    if img is None:
        raise RuntimeError(f"Cannot read image: {input_path}")

    enhanced = _enhance_opencv(img)
    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    gray = _clahe(gray, clip=3.0)
    return cv2.medianBlur(gray, 3)


def enhance_image(input_path: str, output_path: str) -> str:
    """
    Enhance an OMR sheet image and save to output_path.

    Returns output_path for convenience:
        scan_path = enhance_image(raw_path, enhanced_path)
    """
    img = cv2.imread(input_path)
    if img is None:
        raise RuntimeError(f"Cannot read image: {input_path}")
    cv2.imwrite(output_path, _enhance_opencv(img))
    return output_path
