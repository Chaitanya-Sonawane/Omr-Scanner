#!/usr/bin/env python3
"""Test detection on recent uploads"""
import sys
from omr.preprocessor import preprocess
from omr.adaptive_detector import detect_adaptive

img_path = sys.argv[1] if len(sys.argv) > 1 else "data/sessions/336665d9-8d69-4863-9b62-4f0312f83061/sheets/002_raw.jpeg"

print(f"Testing: {img_path}")
img = preprocess(img_path)
result = detect_adaptive(img)

print(f"Flagged: {result.flagged_for_review}")
print(f"Confidence: {result.sheet_confidence}")
print(f"Method: {result.method}")
print(f"\nSample answers:")
for q in result.questions[:5]:
    print(f"Q{q.q_no}: {q.detected_answer} (conf: {q.confidence:.2f})")
