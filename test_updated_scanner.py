#!/usr/bin/env python3
"""
Test script to demonstrate the updated OMR scanner with pen marking detection.

Usage:
    python test_updated_scanner.py <image_path>
    
Example:
    python test_updated_scanner.py samples/sample1/inputs/1.jpg
"""

import sys
import json
from pathlib import Path
from omr_scanner import detect_bubbles, score_sheet

def test_scanner(image_path):
    """Test the updated OMR scanner on an image."""
    print(f"Testing updated OMR scanner on: {image_path}")
    print("=" * 60)
    
    try:
        # Detect bubbles using the updated scanner
        answers, flags, raw_results = detect_bubbles(image_path, debug_out="debug_output.jpg")
        
        print("✅ Detection completed successfully!")
        print(f"\n📊 Results Summary:")
        print(f"   Total questions detected: {len(answers)}")
        print(f"   Flagged questions: {len(flags)}")
        
        # Display detected answers
        print(f"\n📝 Detected Answers:")
        option_map = {1: "A", 2: "B", 3: "C", 4: "D"}
        for q in sorted(answers.keys()):
            answer = answers[q]
            if answer is not None:
                letter = option_map.get(answer, str(answer))
                flag_info = f" (⚠️ {flags[q]})" if q in flags else ""
                print(f"   Q{q:2d}: {letter}{flag_info}")
            else:
                print(f"   Q{q:2d}: (blank)")
        
        # Display flags if any
        if flags:
            print(f"\n⚠️  Flagged Questions:")
            for q, reason in flags.items():
                print(f"   Q{q}: {reason}")
        
        # Show some intensity data for debugging
        print(f"\n🔍 Sample Intensity Data (first 3 questions):")
        for q in sorted(list(raw_results.keys())[:3]):
            intensities = raw_results[q]
            print(f"   Q{q}: {intensities}")
            
        print(f"\n✅ Debug visualization saved to: debug_output.jpg")
        print(f"\nℹ️  This scanner now supports:")
        print(f"   • Pen marks (blue, black, red)")
        print(f"   • Phone camera photos") 
        print(f"   • Adaptive grid calibration")
        print(f"   • Confidence scoring")
        print(f"   • Multi-mark detection")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during detection: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_updated_scanner.py <image_path>")
        print("\nExample:")
        print("  python test_updated_scanner.py samples/sample1/inputs/1.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    if not Path(image_path).exists():
        print(f"❌ Error: Image file not found: {image_path}")
        sys.exit(1)
    
    success = test_scanner(image_path)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()