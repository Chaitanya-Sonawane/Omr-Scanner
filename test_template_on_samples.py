#!/usr/bin/env python3
"""
Test the corrected template on all sample sheets.
Overlays detected bubble positions and shows alignment quality.
"""
import json
import sys
from pathlib import Path
from glob import glob

import cv2
import numpy as np

sys.path.insert(0, 'files(5)')
from align import align_sheet, load_image, CANON_W, CANON_H

# Load corrected template
with open('files(5)/template.json') as f:
    template = json.load(f)

radius = template['radius']

# Find all sample/test images (excluding debug outputs)
sample_patterns = [
    'samples/*.jpg', 'samples/*.png',
    'inputs/*.jpg', 'inputs/*.png',
    './debug_sample*.jpg', './debug_Sample*.jpg',
    './testS.jpg', './test*.jpg',
]

sample_images = []
for pattern in sample_patterns:
    sample_images.extend(glob(pattern))

# Remove duplicates and already-processed debug files
sample_images = list(set(sample_images))
sample_images = [s for s in sample_images if not s.endswith('_overlay.jpg')]
sample_images.sort()

print(f"Found {len(sample_images)} sample images to process")
print("=" * 70)

output_dir = Path('sample_detection_results')
output_dir.mkdir(exist_ok=True)

def sample_bubble_intensity(gray, x, y, radius):
    """Sample mean darkness inside a bubble (0=white, 255=black)."""
    r_sample = max(4, int(radius * 0.72))
    x0, x1 = max(0, x - r_sample), min(gray.shape[1], x + r_sample)
    y0, y1 = max(0, y - r_sample), min(gray.shape[0], y + r_sample)
    patch = gray[y0:y1, x0:x1]
    if patch.size == 0:
        return 0.0
    
    mask = np.zeros(patch.shape, dtype=np.uint8)
    cx, cy = patch.shape[1] // 2, patch.shape[0] // 2
    cv2.circle(mask, (cx, cy), r_sample, 255, -1)
    
    vals = patch[mask == 255]
    if vals.size == 0:
        return 0.0
    
    # Return darkness (inverted so higher = darker)
    darkness = 255.0 - float(vals.mean())
    return darkness

for idx, img_path in enumerate(sample_images, 1):
    print(f"\n[{idx}/{len(sample_images)}] Processing: {img_path}")
    
    try:
        # Load and align
        img = load_image(img_path)
        if img is None:
            print(f"  ✗ Could not load image")
            continue
            
        warped, quality = align_sheet(img, out_size=(CANON_W, CANON_H))
        gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        
        print(f"  Alignment: method={quality['border_method']} "
              f"conf={quality['border_confidence']} blur={quality['blur_score']:.0f}")
        
        # Create overlay
        overlay = warped.copy()
        
        # Draw gridlines (subtle)
        for row_line in template['ref_row_lines']:
            y = int(round(row_line))
            cv2.line(overlay, (0, y), (CANON_W, y), (230, 230, 255), 1)
        
        for col_line in template['ref_col_lines']:
            x = int(round(col_line))
            cv2.line(overlay, (x, 0), (x, CANON_H), (230, 230, 255), 1)
        
        # Sample all 160 bubbles and detect filled ones
        bubble_scores = {}
        for q in range(1, 41):
            for opt in range(1, 5):
                key = f'{q}_{opt}'
                bubble = template['bubbles'][key]
                x, y = int(round(bubble['x'])), int(round(bubble['y']))
                
                darkness = sample_bubble_intensity(gray, x, y, radius)
                bubble_scores[key] = darkness
        
        # Per-sheet adaptive threshold (simple Otsu on all scores)
        scores_array = np.array(list(bubble_scores.values()), dtype=np.float32)
        scores_8u = np.clip(scores_array, 0, 255).astype(np.uint8)
        threshold, _ = cv2.threshold(scores_8u, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        print(f"  Threshold: {threshold:.1f} (min={scores_array.min():.1f} max={scores_array.max():.1f})")
        
        # Detect answers
        detected_answers = {}
        for q in range(1, 41):
            q_scores = [bubble_scores[f'{q}_{opt}'] for opt in range(1, 5)]
            max_score = max(q_scores)
            
            if max_score >= threshold:
                detected_opt = q_scores.index(max_score) + 1
                detected_answers[q] = detected_opt
        
        print(f"  Detected filled: {len(detected_answers)}/40 bubbles")
        
        # Draw all bubbles with color coding
        for q in range(1, 41):
            for opt in range(1, 5):
                key = f'{q}_{opt}'
                bubble = template['bubbles'][key]
                x, y = int(round(bubble['x'])), int(round(bubble['y']))
                darkness = bubble_scores[key]
                
                # Color coding
                if detected_answers.get(q) == opt:
                    # Detected as filled
                    color = (0, 255, 0)  # Green
                    thickness = 3
                    cv2.circle(overlay, (x, y), 4, (0, 255, 0), -1)  # Center dot
                elif darkness >= threshold * 0.7:
                    # Close to threshold (ambiguous)
                    color = (0, 165, 255)  # Orange
                    thickness = 2
                else:
                    # Empty
                    color = (200, 200, 200)  # Gray
                    thickness = 1
                
                cv2.circle(overlay, (x, y), radius, color, thickness)
        
        # Add info overlay
        info_y = 30
        cv2.putText(overlay, f"Sheet: {Path(img_path).name}", (20, info_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3)
        cv2.putText(overlay, f"Sheet: {Path(img_path).name}", (20, info_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        info_y += 35
        cv2.putText(overlay, f"Detected: {len(detected_answers)}/40 | Threshold: {threshold:.0f}", 
                   (20, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
        cv2.putText(overlay, f"Detected: {len(detected_answers)}/40 | Threshold: {threshold:.0f}", 
                   (20, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        info_y += 35
        cv2.putText(overlay, f"Align: {quality['border_confidence']} | Blur: {quality['blur_score']:.0f}", 
                   (20, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
        cv2.putText(overlay, f"Align: {quality['border_confidence']} | Blur: {quality['blur_score']:.0f}", 
                   (20, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Legend
        legend_y = CANON_H - 120
        cv2.putText(overlay, "Legend:", (20, legend_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        legend_y += 25
        cv2.circle(overlay, (30, legend_y), 8, (0, 255, 0), 3)
        cv2.putText(overlay, "= Detected (filled)", (50, legend_y + 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        legend_y += 25
        cv2.circle(overlay, (30, legend_y), 8, (0, 165, 255), 2)
        cv2.putText(overlay, "= Ambiguous (near threshold)", (50, legend_y + 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        legend_y += 25
        cv2.circle(overlay, (30, legend_y), 8, (200, 200, 200), 1)
        cv2.putText(overlay, "= Empty", (50, legend_y + 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Show detected answers summary
        if detected_answers:
            answers_text = ", ".join([f"Q{q}={opt}" for q, opt in sorted(detected_answers.items())[:10]])
            if len(detected_answers) > 10:
                answers_text += f"... (+{len(detected_answers)-10} more)"
            
            summary_y = CANON_H - 50
            cv2.putText(overlay, f"Sample answers: {answers_text}", (20, summary_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
            cv2.putText(overlay, f"Sample answers: {answers_text}", (20, summary_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 255, 100), 1)
        
        # Save
        out_name = f"{Path(img_path).stem}_overlay.jpg"
        out_path = output_dir / out_name
        cv2.imwrite(str(out_path), overlay, [cv2.IMWRITE_JPEG_QUALITY, 92])
        
        print(f"  ✓ Saved: {out_path}")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 70)
print(f"Processing complete. Results saved to: {output_dir}/")
print(f"View results:")
print(f"  ls -lh {output_dir}/")
print(f"  xdg-open {output_dir}/")
