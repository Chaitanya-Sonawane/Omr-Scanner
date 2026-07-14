# OMR Scanner — Template-Based Architecture

This replaces per-sheet circle detection with a **fixed, one-time template** +
per-sheet alignment, exactly per the 4-step plan:

## The 3 files

- **`align.py`** — Warps any photographed sheet into a fixed 1400×2200 canonical
  frame using the printed table's outer border as the 4 anchor points
  (`cv2.warpPerspective`). Adaptive threshold + contour/minAreaRect fallback
  makes this robust to uneven phone lighting, rotation, and skew (tested to
  ±7° rotation + perspective distortion with 0 misreads on a 40-question sheet).

- **`calibrate_template.py`** — **Run this ONCE.** Aligns your cleanest
  reference sheet, then detects the printed gridlines (not bubble circles —
  gridlines are exact and unambiguous on a printed form) to compute all 160
  bubble centers as row/column cell midpoints. Writes `template.json`, which
  is hardcoded from then on. Re-run only if the sheet's printed layout
  changes.

- **`scan_omr.py`** — The production scanner. For every sheet:
  1. Aligns it with `align.py` (no fresh geometry detection).
  2. Reads fill-intensity at the 160 fixed `template.json` coordinates only.
  3. Computes a **per-sheet** Otsu threshold from that sheet's own 160
     intensity values (not a global constant) — this absorbs scan/lighting/pen
     differences between sheets automatically.
  4. Classifies each question as `OK` / `BLANK` / `MULTI` / `REVIEW`. It never
     silently guesses a close call — anything within a small margin of the
     threshold or of a second candidate is flagged `REVIEW`, and two genuinely
     dark bubbles are flagged `MULTI`.

## Usage

```bash
# One-time, only when the printed sheet layout changes:
python3 calibrate_template.py your_cleanest_reference_sheet.jpg

# Every batch scan after that:
python3 scan_omr.py sheet1.jpg sheet2.jpg sheet3.jpg --out omr_results.xlsx
```

Output: `omr_results.xlsx` with one sheet per scanned image (Question,
Selected_Option, Status) plus a `Summary` tab (counts of OK/Blank/Multi/Review
per sheet — use this to see at a glance which sheets need a human to check the
`debug_overlays/` folder before trusting the score).

## Verified on this batch

- Reference sheet: 40/40 questions read `OK`, matching manual inspection exactly.
- Synthetic stress test (7° rotation + perspective skew + padding, simulating
  a sloppy phone photo): 40/40 identical results to the clean scan — 0
  mismatches.
- Classification edge cases unit-tested: clean single mark, blank, genuine
  double-mark (→ MULTI), borderline single mark near the threshold
  (→ REVIEW, not guessed), one clearly-darker-than-others mark despite faint
  noise in another bubble (→ OK).

## Notes for scaling to real batches

- `template.json` is portable — commit it to your repo / `omr-web` backend so
  every worker process shares the exact same coordinates.
- If you ever print the sheet on a different printer/layout, re-run
  `calibrate_template.py` on one clean sample from that print run first.
- `calibrate_template.py` will hard-fail with a clear error if it doesn't find
  exactly 23 horizontal and 11 vertical gridlines, rather than silently
  producing a bad template — inspect `debug_template_overlay.jpg` if that happens.
