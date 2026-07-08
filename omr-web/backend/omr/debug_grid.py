"""
Quick visual debug script — draws the bubble grid on a preprocessed image
and saves it so you can verify alignment without running the full server.

Usage:
  python -m omr.debug_grid path/to/sheet.jpg
"""
import sys
import cv2
import numpy as np
from omr.preprocessor import preprocess
from omr.bubble_detector import (
    _bubble_centres, OPTIONS, BUBBLE_W, BUBBLE_H,
    LEFT_COL_X0, RIGHT_COL_X0, ROW_START_Y, ROW_GAP, OPTION_GAP,
)


def draw_grid(img_path: str, out_path: str = "debug_grid_output.jpg"):
    img = preprocess(img_path)
    vis = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)

    for q in range(1, 41):
        centres = _bubble_centres(q)
        for opt, (cx, cy) in centres.items():
            x0 = cx - BUBBLE_W // 2
            y0 = cy - BUBBLE_H // 2
            x1 = x0 + BUBBLE_W
            y1 = y0 + BUBBLE_H
            cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 255, 0), 1)
            cv2.putText(vis, opt, (cx - 5, cy + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.25, (0, 0, 255), 1)

    cv2.imwrite(out_path, vis)
    print(f"Saved grid overlay to: {out_path}")
    print(f"Image shape: {img.shape}")
    print(f"Grid: LEFT_X0={LEFT_COL_X0} RIGHT_X0={RIGHT_COL_X0} "
          f"ROW_START_Y={ROW_START_Y} ROW_GAP={ROW_GAP} OPTION_GAP={OPTION_GAP}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m omr.debug_grid <image_path> [output_path]")
        sys.exit(1)
    out = sys.argv[2] if len(sys.argv) > 2 else "debug_grid_output.jpg"
    draw_grid(sys.argv[1], out)
