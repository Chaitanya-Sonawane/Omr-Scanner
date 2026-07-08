#!/usr/bin/env python3
"""Debug column mapping"""
import cv2
import numpy as np

def debug_columns(img_path):
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_blur = cv2.medianBlur(gray, 5)
    h, w = gray.shape

    # Detect circles
    circles = cv2.HoughCircles(
        gray_blur, cv2.HOUGH_GRADIENT, dp=1, minDist=15,
        param1=50, param2=18, minRadius=8, maxRadius=25
    )
    if circles is None:
        circles = cv2.HoughCircles(
            gray_blur, cv2.HOUGH_GRADIENT, dp=1, minDist=12,
            param1=40, param2=15, minRadius=6, maxRadius=30
        )
    if circles is None:
        print("No circles found!")
        return
        
    circles = np.round(circles[0]).astype(int)
    circles = [c for c in circles if 50 < c[0] < w - 50 and 250 < c[1] < h - 30]
    
    # Remove outliers
    ys_all = sorted(c[1] for c in circles)
    cut_y = None
    for i in range(1, min(15, len(ys_all))):
        if ys_all[i] - ys_all[i - 1] > 100:
            cut_y = ys_all[i]
    if cut_y is not None:
        circles = [c for c in circles if c[1] >= cut_y]

    pts = np.array([[c[0], c[1]] for c in circles])
    print(f"Found {len(pts)} circles")
    
    # Split left/right
    xs = pts[:, 0].reshape(-1, 1).astype(np.float32)
    if len(set(pts[:, 0])) >= 2:
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, block_labels, block_centers = cv2.kmeans(xs, 2, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
        left_block_id = int(np.argmin(block_centers.flatten()))
        print(f"Block centers: {block_centers.flatten()}")
        print(f"Left block ID: {left_block_id}")
    else:
        print("Not enough x variation for blocks")
        return
    
    # Focus on left block (Q1-20)
    mask = block_labels.flatten() == left_block_id
    block_pts = pts[mask]
    print(f"Left block has {len(block_pts)} circles")
    
    # Find columns in left block
    bxs = block_pts[:, 0].reshape(-1, 1).astype(np.float32)
    if len(set(block_pts[:, 0])) >= 4:
        _, col_labels, col_centers = cv2.kmeans(bxs, 4, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
        col_centers_sorted = sorted(col_centers.flatten().tolist())
        print(f"Column centers (left to right): {col_centers_sorted}")
        
        # Show the cluster mapping
        cluster_order = np.argsort(col_centers.flatten())
        cluster_to_opt = {int(cluster_order[i]): i for i in range(4)}
        print(f"Cluster order: {cluster_order}")
        print(f"Cluster to option mapping: {cluster_to_opt}")
        
        # Show actual column assignments
        for i in range(4):
            cluster_id = cluster_order[i]
            actual_x = col_centers[cluster_id][0]
            print(f"Option {i+1} -> Cluster {cluster_id} at x={actual_x:.1f}")
            
        # Test Q1 specifically
        ys = block_pts[:, 1].astype(np.float64)
        y_min = ys.min()
        
        print(f"\nQ1 sampling positions:")
        for opt_idx in range(4):
            # Find circles assigned to this option
            assigned_circles = []
            for i in range(len(block_pts)):
                if cluster_to_opt.get(int(col_labels[i][0]), -1) == opt_idx:
                    assigned_circles.append(block_pts[i])
            
            if assigned_circles:
                avg_x = np.mean([p[0] for p in assigned_circles])
                print(f"  Option {opt_idx+1}: x={avg_x:.1f}")
    else:
        print("Not enough x variation for columns")

if __name__ == "__main__":
    debug_columns("data/sessions/336665d9-8d69-4863-9b62-4f0312f83061/sheets/001_raw.jpeg")