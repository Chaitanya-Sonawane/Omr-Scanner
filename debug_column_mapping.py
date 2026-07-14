#!/usr/bin/env python3
"""
Debug the column mapping to see what's happening
"""

import cv2
import numpy as np
import sys

# Manually check what the scanner is doing
img_path = sys.argv[1] if len(sys.argv) > 1 else "testS.jpg"

img = cv2.imread(img_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
h, w = gray.shape

# Detect circles
blur = cv2.medianBlur(gray, 5)
circles = cv2.HoughCircles(
    blur, cv2.HOUGH_GRADIENT, dp=1, minDist=18,
    param1=50, param2=18, minRadius=8, maxRadius=30
)

if circles is None:
    print("No circles detected!")
    sys.exit(1)

circles = np.round(circles[0]).astype(int)
print(f"Total circles detected: {len(circles)}")

# Filter
circles = [c for c in circles if 50 < c[0] < w - 50 and 200 < c[1] < h - 30]
print(f"After edge filtering: {len(circles)}")

# Split left/right
x_mid = w / 2.0
left_circles = [c for c in circles if c[0] < x_mid]
print(f"Left block circles: {len(left_circles)}")

# Get x positions
left_x = np.array([c[0] for c in left_circles])

# K-means clustering
from sklearn.cluster import KMeans
X = left_x.reshape(-1, 1)
kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
labels = kmeans.fit_predict(X)
centers = kmeans.cluster_centers_.flatten()

print(f"\nCluster centers (raw): {centers}")
print(f"Cluster centers (sorted): {sorted(centers)}")

# Get cluster order (which cluster is leftmost, etc.)
cluster_order = np.argsort(centers)
print(f"Cluster order (leftmost to rightmost): {cluster_order}")

# Current mapping logic
cluster_to_opt_OLD = {int(cluster_order[i]): i for i in range(4)}
print(f"\nOLD Mapping (cluster_id -> opt_idx):")
for cid, opt in cluster_to_opt_OLD.items():
    print(f"  Cluster {cid} (x≈{centers[cid]:.0f}) -> opt_idx {opt} -> Option {opt+1}")

# Show which circles belong to which cluster
print(f"\nCircle assignments:")
for i, (x, label) in enumerate(zip(left_x[:8], labels[:8])):
    opt_idx = cluster_to_opt_OLD.get(label, -1)
    print(f"  Circle at x={x:.0f} -> Cluster {label} -> opt_idx {opt_idx} -> Option {opt_idx+1}")

# Now show what Q1 answer should be
q1_circles = [(c[0], c[1], labels[i]) for i, c in enumerate(left_circles[:8])]
q1_sorted = sorted(q1_circles, key=lambda x: x[1])[:4]  # Get top 4 (Q1)

print(f"\nQuestion 1 circles (left to right):")
for x, y, label in sorted(q1_sorted, key=lambda c: c[0]):
    opt_idx = cluster_to_opt_OLD.get(label, -1)
    print(f"  x={x:.0f}, y={y:.0f} -> Cluster {label} -> Option {opt_idx+1}")
