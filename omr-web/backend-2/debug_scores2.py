"""
Prints per-question relative analysis to tune thresholds.
"""
import sys
sys.path.insert(0, '.')
import cv2, numpy as np
from align import align_sheet, load_image
from omr_engine import load_template, _normalize_illumination, _grid_correct, _sample_bubble

img_path = sys.argv[1] if len(sys.argv) > 1 else '../../debug_adrian1.jpg'
template = load_template()
img = load_image(img_path)
warped, quality = align_sheet(img, out_size=(template['canon_w'], template['canon_h']))
gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
norm_gray = _normalize_illumination(gray)
radius = template['radius']
correct_xy, grid_matched = _grid_correct(gray, template)

raw_scores = {}
raw_ratios = {}
for key, c in template['bubbles'].items():
    x, y = correct_xy(c['x'], c['y'])
    score, ratio = _sample_bubble(norm_gray, int(round(x)), int(round(y)), radius)
    raw_scores[key] = score
    raw_ratios[key] = ratio

all_vals = list(raw_scores.values())
sheet_min = np.min(all_vals)
sheet_max = np.max(all_vals)
sheet_range = sheet_max - sheet_min
sheet_mean = np.mean(all_vals)

print(f"Sheet: min={sheet_min:.1f} max={sheet_max:.1f} range={sheet_range:.1f} mean={sheet_mean:.1f}")
print()

N = 40
for q in range(1, N+1):
    scores = [raw_scores.get(f"{q}_{o}", 0) for o in range(1, 5)]
    ratios = [raw_ratios.get(f"{q}_{o}", 0) for o in range(1, 5)]
    best = int(np.argmax(scores))
    row_mean = np.mean(scores)
    gap = (scores[best] - sorted(scores, reverse=True)[1]) / sheet_range
    above = (scores[best] - row_mean) / sheet_range
    fill_r = ratios[best]
    print(f"Q{q:2d}: scores={[f'{s:.0f}' for s in scores]}  "
          f"best=OPT{best+1}({scores[best]:.0f})  "
          f"above_mean={above:.3f}  gap={gap:.3f}  fill={fill_r:.2f}")
