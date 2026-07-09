#!/usr/bin/env python3
"""
Quick Test Script for OMR Scanner
Fast way to test a single image or run standard tests
"""

import sys
import os
from omr_scanner import detect_bubbles
import argparse

def quick_test_image(image_path, show_details=False):
    """Quick test of a single image"""
    if not os.path.exists(image_path):
        print(f"❌ File not found: {image_path}")
        return False
    
    print(f"Testing: {image_path}")
    print("-" * 60)
    
    try:
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        debug_out = f"debug_{base_name}_quick.jpg"
        
        answers, flags, raw_results, confidence = detect_bubbles(image_path, debug_out)
        
        # Quick stats
        answered = sum(1 for a in answers.values() if a is not None)
        flagged = len(flags)
        avg_conf = sum(confidence.values()) / 40 if confidence else 0
        
        print(f"✅ Success!")
        print(f"   Answered: {answered}/40 ({answered/40*100:.0f}%)")
        print(f"   Flagged: {flagged}")
        print(f"   Avg Confidence: {avg_conf:.0f}%")
        
        if show_details:
            print(f"\nAnswers:")
            option_map = {1: "A", 2: "B", 3: "C", 4: "D"}
            for q in range(1, 41):
                ans = answers.get(q)
                if ans:
                    letter = option_map[ans]
                    conf = confidence.get(q, 0)
                    flag = f" [{flags[q]}]" if q in flags else ""
                    print(f"   Q{q:2d}: {letter} ({conf:.0f}%){flag}")
                else:
                    print(f"   Q{q:2d}: (blank)")
        
        print(f"\n💾 Debug image: {debug_out}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def run_standard_tests():
    """Run a few standard test images"""
    print("="*60)
    print(" STANDARD TEST IMAGES ".center(60, "="))
    print("="*60)
    
    test_images = [
        "samples/sample6/doc-scans/sample_roll_01.jpg",
        "samples/sample4/IMG_20201116_143512.jpg",
    ]
    
    results = []
    for img in test_images:
        if os.path.exists(img):
            print()
            success = quick_test_image(img, show_details=False)
            results.append((img, success))
    
    print("\n" + "="*60)
    print(f"Results: {sum(1 for _, s in results if s)}/{len(results)} passed")
    print("="*60)

def main():
    parser = argparse.ArgumentParser(description='Quick OMR Scanner Test')
    parser.add_argument('image', nargs='?', help='Image file to test')
    parser.add_argument('-d', '--details', action='store_true', 
                       help='Show detailed answers')
    parser.add_argument('-s', '--standard', action='store_true',
                       help='Run standard test suite')
    
    args = parser.parse_args()
    
    if args.standard:
        run_standard_tests()
    elif args.image:
        quick_test_image(args.image, show_details=args.details)
    else:
        print("Usage:")
        print("  python quick_test.py <image_file>           Test single image")
        print("  python quick_test.py -d <image_file>        Test with details")
        print("  python quick_test.py -s                     Run standard tests")
        print("\nExamples:")
        print("  python quick_test.py samples/sample6/doc-scans/sample_roll_01.jpg")
        print("  python quick_test.py -d samples/sample4/IMG_20201116_143512.jpg")
        print("  python quick_test.py -s")
        sys.exit(1)

if __name__ == "__main__":
    main()
