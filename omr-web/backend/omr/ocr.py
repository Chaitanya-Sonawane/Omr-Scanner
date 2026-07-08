"""
OCR wrapper for student name / roll number extraction from sheet header.
Falls back gracefully if tesseract is unavailable or returns low-confidence text.
"""
import re
from typing import Optional, Tuple

import numpy as np

# Header region: top 15% of the 800×1040 preprocessed image
HEADER_Y_RATIO = 0.15
MIN_OCR_CONFIDENCE = 60  # tesseract word confidence threshold


def _crop_header(img: np.ndarray) -> np.ndarray:
    h = img.shape[0]
    return img[: int(h * HEADER_Y_RATIO), :]


def _parse_student_id(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract roll number and name from raw OCR text."""
    # Roll number: 2–10 consecutive digits
    roll_match = re.search(r"\b(\d{2,10})\b", text)
    roll = roll_match.group(1) if roll_match else None

    # Name: longest sequence of alphabetic tokens (≥2 chars each)
    tokens = re.findall(r"[A-Za-z]{2,}", text)
    name = " ".join(tokens[:4]).strip() if tokens else None  # take up to 4 words

    return roll, name


def extract_student_id(img: np.ndarray, fallback_index: int) -> dict:
    """
    Attempt OCR on the header region.
    Returns:
        { raw_text, student_id, roll_number, name, confidence, used_fallback }
    """
    fallback_id = f"Sheet-{fallback_index}"
    result = {
        "raw_text": "",
        "student_id": fallback_id,
        "roll_number": None,
        "name": None,
        "confidence": 0.0,
        "used_fallback": True,
    }

    try:
        import pytesseract
        from PIL import Image

        header = _crop_header(img)
        # Convert float32 → uint8 for tesseract
        header_u8 = np.clip(header, 0, 255).astype(np.uint8)
        pil_img = Image.fromarray(header_u8)

        data = pytesseract.image_to_data(
            pil_img,
            output_type=pytesseract.Output.DICT,
            config="--psm 6",
        )

        # Filter confident words
        words = []
        confidences = []
        for i, conf in enumerate(data["conf"]):
            try:
                c = int(conf)
            except (ValueError, TypeError):
                continue
            if c >= MIN_OCR_CONFIDENCE:
                w = data["text"][i].strip()
                if w:
                    words.append(w)
                    confidences.append(c)

        if not words:
            return result

        raw_text = " ".join(words)
        mean_conf = float(np.mean(confidences)) / 100.0
        roll, name = _parse_student_id(raw_text)

        # Build a best student_id
        if roll:
            student_id = f"Roll-{roll}" + (f" {name}" if name else "")
        elif name:
            student_id = name
        else:
            student_id = fallback_id

        result.update({
            "raw_text": raw_text,
            "student_id": student_id.strip(),
            "roll_number": roll,
            "name": name,
            "confidence": round(mean_conf, 3),
            "used_fallback": False,
        })

    except Exception:
        # tesseract not installed, image issue, etc. — silently fall back
        pass

    return result
