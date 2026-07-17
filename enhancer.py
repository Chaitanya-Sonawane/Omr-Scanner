"""
Image preprocessing pipeline for OMR sheets - v4.0

Improvements over v3:
  - Image quality validation (blur, brightness, exposure) before processing
  - EXIF-aware orientation correction for phone photos
  - Adaptive shadow removal: kernel tuned to per-image illumination spread
  - Adaptive CLAHE: clip-limit tuned to per-image histogram contrast
  - Adaptive sharpening: strength scaled to measured edge density
  - Guided upscaling for low-resolution inputs (< 800 px wide)
  - Glare/overexposure masking: saturated regions inpainted before thresholding
  - preprocess_for_omr() returns (gray, ImageQuality|None) tuple

Usage:
    from enhancer import preprocess_for_omr, validate_image_quality, enhance_image

    gray, quality = preprocess_for_omr("raw.jpg", validate=True)
    if not quality.is_acceptable:
        print("Bad frame:", quality.reason)
"""

import cv2
import numpy as np
import struct
from dataclasses import dataclass
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Quality assessment
# ---------------------------------------------------------------------------

@dataclass
class ImageQuality:
    """Numeric quality indicators for a captured OMR frame."""
    blur_score: float
    brightness: float
    contrast: float
    overexposed_pct: float
    underexposed_pct: float
    is_acceptable: bool
    reason: str


_MIN_BLUR     = 60.0
_MIN_BRIGHT   = 60.0
_MAX_BRIGHT   = 230.0
_MIN_CONTRAST = 20.0
_MAX_OVEREXP  = 0.15
_MAX_UNDEREXP = 0.25


def validate_image_quality(img_bgr: np.ndarray) -> ImageQuality:
    """Run lightweight quality checks on a BGR image."""
    gray         = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    brightness   = float(np.mean(gray))
    contrast     = float(np.std(gray))
    blur_score   = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    npx          = float(gray.size)
    overexp_pct  = float(np.sum(gray > 245) / npx)
    underexp_pct = float(np.sum(gray < 10)  / npx)

    reasons = []
    if blur_score  < _MIN_BLUR:
        reasons.append(f"blurry (score {blur_score:.0f})")
    if brightness  < _MIN_BRIGHT:
        reasons.append(f"too dark (mean {brightness:.0f})")
    if brightness  > _MAX_BRIGHT:
        reasons.append(f"overexposed (mean {brightness:.0f})")
    if contrast    < _MIN_CONTRAST:
        reasons.append(f"low contrast (std {contrast:.0f})")
    if overexp_pct > _MAX_OVEREXP:
        reasons.append(f"glare ({overexp_pct*100:.1f}% saturated)")
    if underexp_pct > _MAX_UNDEREXP:
        reasons.append(f"shadow ({underexp_pct*100:.1f}% dark)")

    return ImageQuality(
        blur_score=blur_score, brightness=brightness, contrast=contrast,
        overexposed_pct=overexp_pct, underexposed_pct=underexp_pct,
        is_acceptable=len(reasons) == 0, reason="; ".join(reasons),
    )


# ---------------------------------------------------------------------------
# EXIF orientation
# ---------------------------------------------------------------------------

def _apply_exif_rotation(img_bgr: np.ndarray, img_bytes: bytes) -> np.ndarray:
    """Read EXIF orientation tag from raw bytes and rotate pixel data accordingly."""
    try:
        data = img_bytes

        def _get_orient(d: bytes) -> int:
            if len(d) < 12 or d[:2] != b'\xff\xd8':
                return 1
            off = 2
            while off < len(d) - 4:
                marker = d[off:off+2]
                seg_len = struct.unpack('>' + 'H', d[off+2:off+4])[0]
                if marker == b'\xff\xe1':
                    if d[off+4:off+10] != b'Exif\x00\x00':
                        break
                    tiff = d[off+10:]
                    endian = '>' if tiff[:2] == b'MM' else '<'
                    ifd_off = struct.unpack(endian + 'I', tiff[4:8])[0]
                    n = struct.unpack(endian + 'H', tiff[ifd_off:ifd_off+2])[0]
                    for i in range(n):
                        ent = tiff[ifd_off+2+i*12 : ifd_off+2+(i+1)*12]
                        if len(ent) < 12:
                            break
                        if struct.unpack(endian+'H', ent[:2])[0] == 0x0112:
                            return struct.unpack(endian+'H', ent[8:10])[0]
                    break
                off += 2 + seg_len
            return 1

        orient = _get_orient(data)
        if orient == 3:
            return cv2.rotate(img_bgr, cv2.ROTATE_180)
        if orient == 6:
            return cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)
        if orient == 8:
            return cv2.rotate(img_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
    except Exception:
        pass
    return img_bgr


# ---------------------------------------------------------------------------
# Guided upscaling
# ---------------------------------------------------------------------------

def _ensure_min_resolution(img: np.ndarray, min_width: int = 800) -> np.ndarray:
    """Upscale images narrower than min_width so circle detection has enough pixels."""
    h, w = img.shape[:2]
    if w < min_width:
        scale = min_width / w
        img = cv2.resize(img, (int(w * scale), int(h * scale)),
                         interpolation=cv2.INTER_CUBIC)
    return img


# ---------------------------------------------------------------------------
# Adaptive shadow removal
# ---------------------------------------------------------------------------

def _remove_shadow(gray: np.ndarray) -> np.ndarray:
    """
    Adaptive shadow removal.
    Kernel size is tuned to the spatial frequency of the illumination
    non-uniformity: large spread -> large kernel to span shadows;
    uniform lighting -> small kernel to preserve fine detail.
    """
    h, w = gray.shape
    tile = max(1, min(h, w) // 8)
    local_means = [
        float(np.mean(gray[ty:ty+tile, tx:tx+tile]))
        for ty in range(0, h - tile, tile)
        for tx in range(0, w - tile, tile)
    ]
    spread = float(np.std(local_means)) if local_means else 0.0
    k_frac = 0.07 if spread > 20 else 0.04
    k = max(15, int(min(h, w) * k_frac) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    background = cv2.morphologyEx(gray, cv2.MORPH_DILATE, kernel)
    diff = cv2.absdiff(background, gray)
    return cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)


# ---------------------------------------------------------------------------
# Glare / overexposure dampening
# ---------------------------------------------------------------------------

def _dampen_glare(gray: np.ndarray) -> np.ndarray:
    """
    Reduce saturated highlight regions (glare, window reflections).
    Pixels above 245 are inpainted from their local neighbourhood so they
    don't report as blank white paper during thresholding.
    """
    mask = (gray > 245).astype(np.uint8) * 255
    if not np.any(mask):
        return gray
    return cv2.inpaint(gray, mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)


# ---------------------------------------------------------------------------
# Adaptive CLAHE
# ---------------------------------------------------------------------------

def _adaptive_clahe(gray: np.ndarray) -> np.ndarray:
    """
    CLAHE with clip-limit tuned to per-image histogram spread.
    Low-contrast images get a higher clip; high-contrast images get lower clip
    to avoid noise amplification.
    """
    std = float(np.std(gray))
    clip = max(1.5, min(4.0, 4.0 - (std - 10.0) * (2.5 / 50.0)))
    return cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8)).apply(gray)


# ---------------------------------------------------------------------------
# Adaptive sharpening
# ---------------------------------------------------------------------------

def _sharpen(gray: np.ndarray) -> np.ndarray:
    """
    Unsharp-mask sharpening with strength scaled to edge density.
    Blurry images get stronger sharpening; already-sharp images get a mild
    pass to avoid ringing on noise.
    """
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    strength = max(0.2, min(0.6, 0.6 - (blur_score - 100) * (0.4 / 400.0)))
    blur = cv2.GaussianBlur(gray, (0, 0), sigmaX=1.5)
    sharpened = cv2.addWeighted(gray, 1.0 + strength, blur, -strength, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Deskew
# ---------------------------------------------------------------------------

def _deskew(img: np.ndarray) -> np.ndarray:
    """
    Correct rotation up to +/-15 deg using dominant Hough line angle.
    Extended from +/-10 deg to handle phone shots held at steeper angles.
    A morphological close after rotation fills the border pixels that
    warpAffine introduces so they don't get detected as spurious dark edges.
    """
    gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 40, 120, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold=80,
        minLineLength=max(50, img.shape[1] // 8),
        maxLineGap=20,
    )
    if lines is None or len(lines) < 5:
        return img

    angles = []
    for line in lines[:80]:
        x1, y1, x2, y2 = line[0]
        if x2 != x1:
            a = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if abs(a) <= 15:
                angles.append(a)

    if not angles:
        return img

    skew = float(np.median(angles))
    if abs(skew) < 0.3:
        return img

    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), skew, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)

    if rotated.ndim == 2:
        kc = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        rotated = cv2.morphologyEx(rotated, cv2.MORPH_CLOSE, kc, iterations=1)
    return rotated


# ---------------------------------------------------------------------------
# Full colour enhancement pipeline
# ---------------------------------------------------------------------------

def _enhance_opencv(img_bgr: np.ndarray) -> np.ndarray:
    """
    Full colour enhancement pipeline:
      1. Guided upscaling (if < 800 px wide)
      2. Deskew (up to +/-15 deg)
      3. Adaptive shadow removal
      4. Glare/overexposure dampening
      5. Adaptive CLAHE
      6. Adaptive unsharp-mask sharpening
      7. Mild fast NLM denoising
    """
    img_bgr = _ensure_min_resolution(img_bgr)
    img_bgr = _deskew(img_bgr)

    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)

    l_ch = _dampen_glare(l_ch)
    l_no_shadow = _remove_shadow(l_ch)
    l_eq = _adaptive_clahe(l_no_shadow)

    enhanced = cv2.cvtColor(cv2.merge([l_eq, a_ch, b_ch]), cv2.COLOR_LAB2BGR)

    sharpened = cv2.merge([_sharpen(c) for c in cv2.split(enhanced)])

    return cv2.fastNlMeansDenoisingColored(
        sharpened, None, h=4, hColor=4,
        templateWindowSize=7, searchWindowSize=21,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def preprocess_for_omr(
    input_path: str,
    validate: bool = False,
) -> Tuple[np.ndarray, Optional[ImageQuality]]:
    """
    Load an image, optionally validate quality, enhance it, and return a
    preprocessed grayscale ndarray ready for circle detection.

    Pipeline:
        EXIF rotation -> upscale -> _enhance_opencv -> grayscale ->
        adaptive CLAHE -> glare dampening -> median blur

    Returns
    -------
    gray    : np.ndarray  uint8 grayscale ready for detection
    quality : ImageQuality or None (when validate=False)
    """
    with open(input_path, 'rb') as fh:
        raw_bytes = fh.read()

    img = cv2.imdecode(np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"Cannot read image: {input_path}")

    img = _apply_exif_rotation(img, raw_bytes)

    quality = validate_image_quality(img) if validate else None

    enhanced = _enhance_opencv(img)
    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    gray = _adaptive_clahe(gray)
    gray = cv2.medianBlur(gray, 3)
    return gray, quality


def enhance_image(input_path: str, output_path: str) -> str:
    """Enhance an OMR sheet image and save to output_path. Returns output_path."""
    with open(input_path, 'rb') as fh:
        raw_bytes = fh.read()
    img = cv2.imdecode(np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"Cannot read image: {input_path}")
    img = _apply_exif_rotation(img, raw_bytes)
    cv2.imwrite(output_path, _enhance_opencv(img))
    return output_path
