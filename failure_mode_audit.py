"""
Failure-mode audit for the OMR scanner pipeline.

Runs the EXISTING real-photo test set through the CURRENT (unmodified)
detection pipeline and buckets every observed per-question warning into the
categories requested by the engineering brief (Section 4):

  - Misalignment / skew error
  - Lighting / thresholding error
  - Ambiguous-mark classification error (multi-mark / light / stray)
  - Other (named explicitly)

This is a *reporting* tool only — it does not modify the pipeline.
Run from the repo root:  python3 failure_mode_audit.py
"""

import os
import sys
import glob
from collections import Counter

# Use the same scanner the API uses.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "omr-web", "backend"))
import omr.omr_scanner as omr_scanner  # noqa: E402

# Map raw internal flags -> audit buckets (Section 4 of the brief).
FLAG_TO_BUCKET = {
    "multi_mark": "Ambiguous-mark classification error",
    "low_confidence": "Lighting / thresholding error",
    "row_smudged": "Lighting / thresholding error",
    "no_clear_mark": "Other (blank / no mark detected)",
}

REAL_PHOTO_DIRS = ["SAMPLESSHEET", "samples", "inputs"]


def find_photos():
    photos = []
    root = os.path.dirname(__file__)
    for d in REAL_PHOTO_DIRS:
        p = os.path.join(root, d)
        if os.path.isdir(p):
            for ext in ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG"):
                photos.extend(glob.glob(os.path.join(p, ext)))
    return sorted(set(photos))


def audit():
    photos = find_photos()
    if not photos:
        print("No real-photo test images found in", REAL_PHOTO_DIRS)
        return

    print(f"Auditing {len(photos)} real photo(s) through the CURRENT pipeline\n")
    bucket_counts = Counter()
    per_sheet = []
    total_questions = 0
    total_answered = 0
    total_low_conf = 0

    for path in photos:
        name = os.path.basename(path)
        try:
            answers, flags, _raw, confidence = omr_scanner.detect_bubbles(path)
        except Exception as e:  # sheet-level failure = misalignment/detection
            bucket_counts["Misalignment / skew error"] += 1
            per_sheet.append((name, "SHEET FAILURE", str(e)[:60]))
            continue

        answered = sum(1 for q in answers if answers.get(q) is not None)
        total_questions += len(answers)
        total_answered += answered
        avg_conf = 0
        if confidence:
            avg_conf = int(sum(confidence.values()) / max(1, len(confidence)))
        low = sum(1 for q, c in confidence.items() if c and c < 45)
        total_low_conf += low

        sheet_buckets = Counter()
        for q, f in flags.items():
            # a "no_clear_mark" on an answered question is not an error
            if f == "no_clear_mark" and answers.get(q) is None:
                continue
            bucket = FLAG_TO_BUCKET.get(f, f"Other ({f})")
            bucket_counts[bucket] += 1
            sheet_buckets[bucket] += 1

        per_sheet.append((name, f"{answered}/{len(answers)} ans, "
                                f"avg_conf {avg_conf}%, low_conf {low}",
                          dict(sheet_buckets)))

    print("Per-sheet summary:")
    for name, summary, buckets in per_sheet:
        print(f"  - {name}: {summary}  {buckets}")

    print("\n=== FAILURE-MODE BREAKDOWN (counted, real photos) ===")
    if not bucket_counts:
        print("  No warnings raised across the test set.")
    for bucket, n in bucket_counts.most_common():
        print(f"  {n:4d}  {bucket}")

    print("\nTotals: "
          f"{total_answered}/{total_questions} questions answered, "
          f"{total_low_conf} low-confidence reads.")


if __name__ == "__main__":
    audit()
