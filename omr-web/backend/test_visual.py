#!/usr/bin/env python3
"""Visual test of OMR scanner"""
import cv2
import numpy as np
from omr.omr_scanner import detect_bubbles

img_path = "data/sessions/336665d9-8d69-4863-9b62-4f0312f83061/sheets/001_raw.jpeg"
debug_out = "debug_visual_test.jpg"

print("Testing visual detection...")
answers, flags, raw, _conf = detect_bubbles(img_path, debug_out)

print("Generated debug image: debug_visual_test.jpg")
print("Manual verification needed:")
print("Q1: Scanner says", answers.get(1), "- Check if option 1/2/3/4 is marked")
print("Q2: Scanner says", answers.get(2), "- Check if option 1/2/3/4 is marked") 
print("Q3: Scanner says", answers.get(3), "- Check if option 1/2/3/4 is marked")
print("Q4: Scanner says", answers.get(4), "- Check if option 1/2/3/4 is marked")
print("Q5: Scanner says", answers.get(5), "- Check if option 1/2/3/4 is marked")

# Show raw intensities for first few questions  
for q in range(1, 6):
    if q in raw:
        intensities = raw[q]
        sorted_opts = sorted(intensities.items(), key=lambda x: x[1])
        print(f"Q{q} intensities: {intensities} → darkest: {sorted_opts[0]}")