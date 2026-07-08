#!/usr/bin/env python3
"""
Debug script to visualize bubble detection and tune parameters.
Usage: python debug_detection.py <image_path>
"""
import sys
import cv2
import numpy as np
from omr.preprocessor import preprocess

def debug_circles(img_path: str):
    """Visualize circle detection with various parameter sets."""
    print(f"Loading and preprocessing: {img_path}")
    img = preprocess(img_path)
    img_u8 = np.clip(img, 0, 255).astype(np.uint8)
    
    # Test different parameter combinations
    param_sets = [
        # (dp, minDist, param1, param2, minR, maxR, name)
        (1, 25, 80, 20, 10, 22, "Original"),
        (1, 20, 60, 18, 8, 25, "More Sensitive"),
        (1, 30, 100, 25, 12, 20, "More Strict"),
        (1, 15, 50, 15, 8, 30, "Very Sensitive"),
    ]
    
    for dp, minDist, p1, p2, minR, maxR, name in param_sets:
        blurred = cv2.medianBlur(img_u8, 5)
        circles = cv2.HoughCircles(
            blurred, cv2.HOUGH_GRADIENT,
            dp=dp, minDist=minDist,
            param1=p1, param2=p2,
            minRadius=minR, maxRadius=maxR
        )
        
        count = len(circles[0]) if circles is not None else 0
        print(f"{name}: {count} circles detected")
        
        if circles is not None and count > 0:
            # Visualize
            vis = cv2.cvtColor(img_u8, cv2.COLOR_GRAY2BGR)
            for (x, y, r) in circles[0]:
                cv2.circle(vis, (int(x), int(y)), int(r), (0, 255, 0), 2)
                cv2.circle(vis, (int(x), int(y)), 2, (0, 0, 255), 3)
            
            out_path = f"debug_{name.replace(' ', '_')}.jpg"
            cv2.imwrite(out_path, vis)
            print(f"  -> Saved visualization to {out_path}")
    
    print(f"\nImage shape: {img.shape}")
    print(f"Image dtype: {img.dtype}")
    print(f"Image range: [{img.min():.1f}, {img.max():.1f}]")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_detection.py <image_path>")
        sys.exit(1)
    debug_circles(sys.argv[1])
