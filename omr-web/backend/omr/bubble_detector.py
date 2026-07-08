"""
Bubble detection on a preprocessed 800x1040 grayscale image.
Fixed coordinate grid for 40 questions × 4 options (A/B/C/D).
Two-tier thresholding: global + per-strip local.
Returns structured detection result including per-question confidence.

Grid calibrated for the NMMS Marathi student answer sheet (phone-camera photos):
  Page 800×1040 after preprocessing.

  Layout (measured from sample images):
  ┌─────────────────────────────────────────────────────────┐
  │  Student name (handwritten, ~40px)                      │
  │  Logo + 3 title lines (~130px)                          │
  │  प.क्र. / प्राप्त गुण row (~35px)                       │
  │  Column header (प्रश्न क्र. | 1|2|3|4 | ... | 1|2|3|4) │  ← y≈220
  ├──────────────────────────────────────────────────────────┤
  │  Row 1  (Q1 / Q21)                                      │  ← y≈255
  │  Row 2  ...                                             │  ← y≈293
  │  ...  row pitch ≈ 38px                                  │
  │  Row 20 (Q20 / Q40)                                     │  ← y≈977
  └──────────────────────────────────────────────────────────┘

  Left half  (Q1–Q20):  option-A centre x≈110, pitch=52px  → A=110 B=162 C=214 D=266
  Right half (Q21–Q40): option-A centre x≈470, pitch=52px  → A=470 B=522 C=574 D=626
"""
from dataclasses import dataclass
from typing import Dict, List
import numpy as np

# ── Grid configuration ──────────────────────────────────────────────────────
BUBBLE_W = 26          # ROI width  (bubbles are ~20px circles, 26px ROI adds margin)
BUBBLE_H = 26          # ROI height
OPTIONS = ["A", "B", "C", "D"]

OPTION_GAP = 52        # horizontal centre-to-centre distance between options

LEFT_COL_X0  = 110     # x of option-A centre, left  column (Q1–Q20)
RIGHT_COL_X0 = 470     # x of option-A centre, right column (Q21–Q40)
ROW_START_Y  = 255     # y centre of row 1 (Q1 / Q21)
ROW_GAP      = 38      # vertical centre-to-centre distance between rows

# ── Threshold / confidence parameters ───────────────────────────────────────
MIN_JUMP           = 15   # minimum intensity gap to count as a real jump
CONFIDENT_SURPLUS  = 10   # extra gap needed to prefer local over global threshold
# Lower than 0.60 to avoid false-flagging phone-camera sheets with pen fills
CONFIDENCE_THRESHOLD = 0.40


@dataclass
class QuestionDetection:
    q_no: int
    bubble_intensities: Dict[str, float]
    local_threshold: float
    detected_answer: str   # "", "MULTI", or "A"/"B"/"C"/"D"
    is_blank: bool
    is_multi_marked: bool
    confidence: float      # 0.0–1.0


@dataclass
class SheetDetection:
    questions: List[QuestionDetection]
    global_threshold: float
    sheet_confidence: float
    flagged_for_review: bool


def _bubble_mean(img: np.ndarray, cx: int, cy: int) -> float:
    """Mean intensity of a bubble ROI centred at (cx, cy)."""
    x0 = max(0, cx - BUBBLE_W // 2)
    y0 = max(0, cy - BUBBLE_H // 2)
    x1 = min(img.shape[1], x0 + BUBBLE_W)
    y1 = min(img.shape[0], y0 + BUBBLE_H)
    roi = img[y0:y1, x0:x1]
    return float(np.mean(roi))


def _bubble_centres(q_no: int) -> Dict[str, tuple]:
    """Return {option: (cx, cy)} for question q_no (1-indexed)."""
    if q_no <= 20:
        row = q_no - 1
        x0 = LEFT_COL_X0
    else:
        row = q_no - 21
        x0 = RIGHT_COL_X0
    cy = ROW_START_Y + row * ROW_GAP
    return {opt: (x0 + i * OPTION_GAP, cy) for i, opt in enumerate(OPTIONS)}


def _global_threshold(all_vals: List[float], looseness: int = 4) -> float:
    """Midpoint of the largest intensity gap in sorted values."""
    q_vals = sorted(all_vals)
    ls = (looseness + 1) // 2
    length = len(q_vals) - ls
    max_jump = MIN_JUMP
    thr = 128.0
    for i in range(ls, length):
        jump = q_vals[i + ls] - q_vals[i - ls]
        if jump > max_jump:
            max_jump = jump
            thr = q_vals[i - ls] + jump / 2.0
    return thr


def _local_threshold(strip_vals: List[float], global_thr: float) -> float:
    """Largest gap in this strip. Falls back to global_thr if not confident."""
    q_vals = sorted(strip_vals)
    n = len(q_vals)
    if n < 2:
        return global_thr

    max_jump = 0.0
    thr = global_thr
    for i in range(1, n):
        jump = q_vals[i] - q_vals[i - 1]
        if jump > max_jump:
            max_jump = jump
            thr = q_vals[i - 1] + jump / 2.0

    if max_jump < (MIN_JUMP + CONFIDENT_SURPLUS):
        return global_thr
    return thr


def _question_confidence(strip_vals: List[float], local_thr: float) -> float:
    """
    How clearly one bubble is filled relative to the others.
    Returns 0.0–1.0.
    """
    vals = sorted(strip_vals)
    min_val = vals[0]
    second_val = vals[1] if len(vals) > 1 else local_thr

    below_gap = local_thr - min_val
    above_gap = second_val - local_thr

    if below_gap <= 0 or above_gap <= 0:
        return max(0.0, min(1.0, (local_thr - min_val) / 255.0))

    return min(1.0, (below_gap + above_gap) / 255.0)


def detect(img: np.ndarray) -> SheetDetection:
    """
    Run full bubble detection on a preprocessed 800×1040 sheet image.
    Returns SheetDetection with per-question results and sheet-level confidence.
    """
    # Step 1: collect all 160 bubble intensities
    all_intensities: List[float] = []
    strip_intensities: Dict[int, Dict[str, float]] = {}

    for q in range(1, 41):
        centres = _bubble_centres(q)
        strip = {opt: _bubble_mean(img, cx, cy) for opt, (cx, cy) in centres.items()}
        strip_intensities[q] = strip
        all_intensities.extend(strip.values())

    # Step 2: global threshold
    global_thr = _global_threshold(all_intensities)

    # Step 3: per-question detection
    questions: List[QuestionDetection] = []
    for q in range(1, 41):
        strip = strip_intensities[q]
        vals = list(strip.values())

        local_thr = _local_threshold(vals, global_thr)
        filled = [opt for opt, v in strip.items() if v < local_thr]

        is_blank = len(filled) == 0
        is_multi = len(filled) > 1

        if is_blank:
            detected = ""
        elif is_multi:
            # For multi-marked, pick the darkest single bubble as best guess
            detected = min(strip, key=strip.get)
            is_multi = True
        else:
            detected = filled[0]

        conf = _question_confidence(vals, local_thr)

        questions.append(QuestionDetection(
            q_no=q,
            bubble_intensities=strip,
            local_threshold=round(local_thr, 2),
            detected_answer=detected,
            is_blank=is_blank,
            is_multi_marked=is_multi,
            confidence=round(conf, 4),
        ))

    sheet_conf = round(float(np.mean([q.confidence for q in questions])), 4)
    flagged = sheet_conf < CONFIDENCE_THRESHOLD

    return SheetDetection(
        questions=questions,
        global_threshold=round(global_thr, 2),
        sheet_confidence=sheet_conf,
        flagged_for_review=flagged,
    )
