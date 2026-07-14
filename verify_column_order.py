#!/usr/bin/env python3
"""
Verify that columns are being detected in the correct order (left to right = options 1,2,3,4)
"""

import cv2
import numpy as np
import sys

def visualize_column_detection(img_path):
    """Show which columns are mapped to which options"""
    
    print("="*70)
    print(" COLUMN ORDER VERIFICATION ".center(70, "="))
    print("="*70)
    
    img = cv2.imread(img_path)
    if img is None:
        print(f"Error: Cannot read {img_path}")
        return
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    
    print(f"\nImage: {w}x{h}")
    
    # Detect circles
    blur = cv2.medianBlur(gray, 5)
    circles = cv2.HoughCircles(
        blur, cv2.HOUGH_GRADIENT, dp=1, minDist=18,
        param1=50, param2=18, minRadius=8, maxRadius=30
    )
    
    if circles is None:
        print("No circles detected!")
        return
    
    circles = np.round(circles[0]).astype(int)
    print(f"Detected {len(circles)} circles")
    
    # Filter to main area
    circles = [c for c in circles if 50 < c[0] < w - 50 and 200 < c[1] < h - 30]
    print(f"After filtering: {len(circles)} circles")
    
    if len(circles) < 8:
        print("Too few circles!")
        return
    
    # Split left/right blocks
    x_mid = w / 2.0
    left_circles = [c for c in circles if c[0] < x_mid]
    right_circles = [c for c in circles if c[0] >= x_mid]
    
    print(f"\nLeft block: {len(left_circles)} circles")
    print(f"Right block: {len(right_circles)} circles")
    
    # Analyze left block columns
    print("\n" + "="*70)
    print("LEFT BLOCK (Q1-Q20) - Column Analysis")
    print("="*70)
    
    if len(left_circles) >= 4:
        left_x = sorted([c[0] for c in left_circles])
        
        # Find column centers by clustering x-positions
        from sklearn.cluster import KMeans
        X = np.array(left_x).reshape(-1, 1)
        kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        kmeans.fit(X)
        
        col_centers = sorted(kmeans.cluster_centers_.flatten())
        
        print(f"\nColumn X-positions (left to right):")
        for i, x_pos in enumerate(col_centers):
            print(f"  Column {i+1} (Option {i+1}): x = {x_pos:.0f}")
        
        # Visual output
        vis_img = img.copy()
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]  # B, G, R, Yellow
        color_names = ["BLUE (1)", "GREEN (2)", "RED (3)", "YELLOW (4)"]
        
        for c in left_circles:
            cx, cy = c[0], c[1]
            # Find which column this belongs to
            dists = [abs(cx - center) for center in col_centers]
            col_idx = np.argmin(dists)
            
            cv2.circle(vis_img, (cx, cy), 15, colors[col_idx], 2)
            cv2.putText(vis_img, str(col_idx + 1), (cx - 5, cy + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors[col_idx], 2)
        
        # Add column labels
        y_pos = 150
        for i, x_pos in enumerate(col_centers):
            cv2.line(vis_img, (int(x_pos), y_pos), (int(x_pos), h - 50), colors[i], 1)
            cv2.putText(vis_img, f"Opt{i+1}", (int(x_pos) - 20, y_pos - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors[i], 2)
        
        # Add legend
        legend_y = 50
        for i, color_name in enumerate(color_names):
            cv2.putText(vis_img, color_name, (10, legend_y + i * 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors[i], 2)
        
        cv2.imwrite('column_order_verification.jpg', vis_img)
        print(f"\n✅ Visualization saved: column_order_verification.jpg")
        print(f"\nColor coding:")
        for i, name in enumerate(color_names):
            print(f"  {name}: Should be option {i+1}")
        
        print("\n" + "="*70)
        print("VERIFICATION STEPS:")
        print("="*70)
        print("1. Open: column_order_verification.jpg")
        print("2. Check if the leftmost column is marked as '1' (BLUE)")
        print("3. Check if columns go 1, 2, 3, 4 from left to right")
        print("4. If the order is wrong, we need to fix the column sorting logic")
        
    else:
        print("Not enough circles in left block!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_column_order.py <image_path>")
        print("\nThis will create 'column_order_verification.jpg' showing:")
        print("  - Which columns map to which options")
        print("  - Color coded: BLUE=1, GREEN=2, RED=3, YELLOW=4")
        sys.exit(1)
    
    try:
        visualize_column_detection(sys.argv[1])
    except ImportError:
        print("\n❌ sklearn not installed. Installing...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "scikit-learn"])
        print("\n✅ Installed. Please run again.")
