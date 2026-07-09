#!/usr/bin/env python3
"""Create visual verification of scanner sampling points"""
import cv2
import numpy as np
from omr.omr_scanner import detect_bubbles

def create_visual_debug():
    img_path = "data/sessions/336665d9-8d69-4863-9b62-4f0312f83061/sheets/001_raw.jpeg"
    
    # Run the scanner with debug output
    answers, flags, raw, _conf = detect_bubbles(img_path, "scanner_debug.jpg")
    
    # Load the original image
    img = cv2.imread(img_path)
    
    # Add text annotations for first 5 questions
    font = cv2.FONT_HERSHEY_SIMPLEX
    colors = [(0,0,255), (0,255,0), (255,0,0), (255,255,0)]  # Red, Green, Blue, Yellow for options 1,2,3,4
    
    for q in range(1, 6):
        if q in raw:
            intensities = raw[q]
            detected = answers.get(q, 0)
            
            # Find approximate positions (this is rough estimation)
            base_y = 320 + (q-1) * 50  # Approximate row positions
            base_x = 350  # Approximate starting x for left block
            
            for opt in range(1, 5):
                x = base_x + (opt-1) * 90  # Approximate column spacing
                y = base_y
                
                # Color based on detection
                color = colors[opt-1] if detected == opt else (128,128,128)
                intensity = intensities.get(opt, 255)
                
                # Draw circle and intensity value
                cv2.circle(img, (x, y), 15, color, 2)
                cv2.putText(img, f"{intensity:.0f}", (x-20, y+35), font, 0.4, color, 1)
            
            # Add question info
            cv2.putText(img, f"Q{q}: Detected={detected}", (200, base_y), font, 0.6, (255,255,255), 2)
    
    # Save annotated image
    cv2.imwrite("visual_verify.jpg", img)
    print("Created visual_verify.jpg with annotations")
    
    # Print comparison
    print("\nManual vs Scanner comparison:")
    print("Look at the original sheet image and compare:")
    print("Q1: Scanner detected option", answers.get(1))
    print("Q2: Scanner detected option", answers.get(2)) 
    print("Q3: Scanner detected option", answers.get(3))
    print("Q4: Scanner detected option", answers.get(4))
    print("Q5: Scanner detected option", answers.get(5))
    
    print("\nIntensity values (lower = darker/filled):")
    for q in range(1, 6):
        if q in raw:
            intensities = raw[q]
            sorted_opts = sorted(intensities.items(), key=lambda x: x[1])
            print(f"Q{q}: {intensities}")
            print(f"     Darkest: Option {sorted_opts[0][0]} (intensity {sorted_opts[0][1]:.1f})")

if __name__ == "__main__":
    create_visual_debug()