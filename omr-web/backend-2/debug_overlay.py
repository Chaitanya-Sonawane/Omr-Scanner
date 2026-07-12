"""
Generates a visual debug overlay showing exactly where each bubble
centre is being sampled on the warped sheet.
"""
import sys, json
sys.path.insert(0, '.')

import cv2
import numpy as np
from pathlib import Path
from align import align_sheet, load_image
from omr_engine import load_template, _normalize_illumination, _grid_correct, _sample_bubble

img_path = sys.argv[1] if len(sys.argv) > 1 else '../../debug_adrian1.jpg'
out_path = sys.argv[2] if len(sys.argv) > 2 else 'debug_overlay_out.jpg'

template = load_template()
img = load_image(img_path)
warped, quality = align_sheet(img, out_size=(template['canon_w'], template['canon_h']))
gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
norm_gray = _normalize_illumination(gray)
radius = template['radius']

correct_xy, grid_matched = _grid_correct(gray, template)
print(f"grid_matched: {grid_matched}, quality: {quality}")

# Draw all bubble sample points
dbg = warped.copy()
for key, c in template['bubbles'].items():
    x, y = correct_xy(c['x'], c['y'])
    xi, yi = int(round(x)), int(round(y))
    score, _ = _sample_bubble(norm_gray, xi, yi, radius)
    # colour by darkness: green=dark(filled), red=light(blank)
    intensity = min(255, int(score * 2))
    color = (0, intensity, 255 - intensity)
    cv2.circle(dbg, (xi, yi), radius, color, 2)
    cv2.circle(dbg, (xi, yi), 2, color, -1)
    q, opt = key.split('_')
    cv2.putText(dbg, f"{score:.0f}", (xi - radius, yi - radius - 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 0, 200), 1)

cv2.imwrite(out_path, dbg)
print(f"Wrote {out_path}")
