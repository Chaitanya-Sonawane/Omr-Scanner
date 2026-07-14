"""
PRODUCTION-GRADE OMR SCANNER - Maximum Accuracy System
========================================================
Golden Rule: NEVER GUESS - Return UNCERTAIN rather than incorrect results

Key Improvements over original:
1. Template-based registration for perfect alignment
2. Multi-criteria bubble validation (9+ checks per bubble)
3. Advanced fill analysis with multiple algorithms
4. Two-pass verification system
5. Per-question confidence scoring with detailed reasoning
6. Robust handling of shadows, tilt, lighting variations
7. Smart detection of circled vs filled bubbles
8. Comprehensive debug logging and visualization

"""
import cv2
import numpy as np
from typing import Tuple, Dict, Optional, List
from dataclasses import dataclass
import sys

# Configuration Constants
class CFG:
    TOTAL_Q = 40
    OPTIONS = 4
    MIN_CONFIDENCE = 60
    FILL_THRESHOLD_STRICT = 0.28  # Fraction of pixels that must be dark
    FILL_THRESHOLD_LENIENT = 0.20
    DARKNESS_THRESHOLD = 0.75  # Intensity must be below this * median_blank
    MIN_GAP_TO_SECOND = 0.12  # Relative gap between 1st and 2nd darkest
    MULTI_MARK_THRESHOLD = 0.10
    DEBUG = False

@dataclass
class BubbleMetrics:
    intensity_mean: float
    intensity_median: float
    intensity_std: float
    filled_pixel_ratio: float
    darkness_score: float
    edge_score: float
    
def log(msg: str):
    if CFG.DEBUG:
        print(f"[OMR] {msg}")

# ============================================================================
# STAGE 1: ADVANCED PREPROCESSING
# ============================================================================

def preprocess_image(img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Advanced preprocessing pipeline"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
    h, w = gray.shape
    
    # Normalize