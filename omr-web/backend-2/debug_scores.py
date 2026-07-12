"""
Prints all raw bubble scores sorted, to understand the actual fill distribution.
"""
import sys, json
sys.path.insert(0, '.')
import cv2, numpy as np
from align import align_sheet, load_image
from omr_engine import load_template, _normalize_illumination, _grid_correct, _sample_bubble, _per_sheet_threshold

img_path = sys.argv[1] if len(sys.argv) > 1 else '../../debug_adrian1.jpg'
template = load_template()
img = load_image(img_path)
warped, quality = align_sheet(img, out_size=(template['canon_w'], template['canon_h']))
gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
norm_gray = _normalize_illumination(gray)
radius = template['radius']
correct_xy, grid_matched = _grid_correct(gray, template)

raw_scores = {}
for key, c in template['bubbles'].items():
    x, y = correct_xy(c['x'], c['y'])
    score, _ = _sample_bubble(norm_gray, int(round(x)), int(round(y)), radius)
    raw_scores[key] = score

thr = _per_sheet_threshold(list(raw_scores.values()))
print(f"Threshold: {thr['threshold']:.1f}")
print(f"Score range: {thr['score_min']:.1f} - {thr['score_max']:.1f}")
print(f"Otsu: {thr['otsu']:.1f}, Kmeans: {thr['kmeans']:.1f}")
print()

# Per-question: show all 4 option scores
N = 40
for q in range(1, N+1):
    scores = [raw_scores.get(f"{q}_{o}", 0) for o in range(1, 5)]
    best = max(range(4), key=lambda i: scores[i])
    marker = f"  <- OPT {best+1}" if scores[best] >= thr['threshold'] else "  (BLANK)"
    print(f"Q{q:2d}: {[f'{s:5.1f}' for s in scores]}  max={scores[best]:.1f}{marker}")
