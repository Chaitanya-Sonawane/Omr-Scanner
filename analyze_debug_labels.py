#!/usr/bin/env python3
"""
Analyze the debug image to extract and verify circle labels
"""

import cv2
import numpy as np
from PIL import Image
import pytesseract

img = cv2.imread('debug_uploaded_test.jpg')
h, w = img.shape[:2]

print("="*70)
print(" DEBUG IMAGE LABEL ANALYSIS ".center(70, "="))
print("="*70)
print(f"\nImage size: {w}x{h}")

# Look for circles (green for unfilled, orange for filled)
# Green circles: (0, 255, 0)
# Orange circles: (0, 165, 255)

green_mask = cv2.inRange(img, (0, 250, 0), (5, 255, 5))
orange_mask = cv2.inRange(img, (0, 160, 250), (5, 170, 255))

green_circles = cv2.countNonZero(green_mask)
orange_circles = cv2.countNonZero(orange_mask)

print(f"\nCircle markers found:")
print(f"  Green (unfilled): {green_circles} pixels")
print(f"  Orange (filled): {orange_circles} pixels")

# Find contours to locate circles
contours_green, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contours_orange, _ = cv2.findContours(orange_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

total_circles = len(contours_green) + len(contours_orange)
print(f"  Total circle contours: {total_circles}")

# Expected: 160 circles (40 questions × 4 options)
print(f"  Expected: 160 circles (40 questions × 4 options)")

if total_circles > 100:
    print(f"  ✓ Circle detection looks good")
else:
    print(f"  ⚠ Fewer circles than expected")

# Look for the first question (Q1) area
# Q1 should be in the upper left portion
print(f"\n" + "="*70)
print("Checking Q1 labels...")
print("="*70)

# Crop Q1 area (roughly top-left)
q1_region = img[250:350, 50:400]
cv2.imwrite('q1_region_debug.jpg', q1_region)
print(f"Extracted Q1 region and saved to: q1_region_debug.jpg")
print(f"Please check this image to see the labels for Question 1")

print(f"\n" + "="*70)
print("EXPECTED LABELS:")
print("="*70)
print("For Question 1, you should see 4 circles labeled:")
print("  1.1 (leftmost) = Option 1 (A)")
print("  1.2            = Option 2 (B)")
print("  1.3            = Option 3 (C)")
print("  1.4 (rightmost) = Option 4 (D)")
print("")
print("The filled circle should be 1.4 (since correct answer for Q1 is D/4)")

print(f"\n" + "="*70)
print("ACTION REQUIRED:")
print("="*70)
print("Please open 'q1_region_debug.jpg' and tell me:")
print("1. What labels do you see on the 4 circles?")
print("2. Which circle is marked as filled (orange color)?")
print("3. Does the label match the filled circle?")
