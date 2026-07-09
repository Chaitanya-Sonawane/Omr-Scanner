#!/usr/bin/env python3
"""
Diagnostic script to analyze OMR detection issues
Shows what the scanner sees vs what should be detected
"""

import sys
import cv2
import numpy as np
from omr_scanner import detect_bubbles

def analyze_image(img_path):
    """Detailed analysis of what the scanner detects"""
    
    print("="*70)
    print(" OMR SHEET DIAGNOSTIC ANALYSIS ".center(70, "="))
    print("="*70)
    
    # Read image info
    img = cv2.imread(img_path)
    if img is None:
        print(f"❌ Cannot read image: {img_path}")
        return
    
    h, w = img.shape[:2]
    print(f"\nImage Info:")
    print(f"  File: {img_path}")
    print(f"  Dimensions: {w}x{h}")
    print(f"  Aspect Ratio: {w/h:.2f}")
    
    # Run detection
    print(f"\n{'='*70}")
    print("Running Scanner...")
    print(f"{'='*70}")
    
    try:
        answers, flags, raw_results, confidence = detect_bubbles(
            img_path, 
            debug_out="debug_diagnostic.jpg"
        )
        
        print(f"\n✅ Detection completed successfully!")
        
        # Statistics
        answered = sum(1 for a in answers.values() if a is not None)
        flagged = len(flags)
        avg_conf = np.mean([confidence.get(q, 0) for q in range(1, 41)])
        
        print(f"\nOverall Statistics:")
        print(f"  Answered: {answered}/40 ({answered/40*100:.0f}%)")
        print(f"  Flagged: {flagged}")
        print(f"  Avg Confidence: {avg_conf:.0f}%")
        
        # Show all answers with confidence
        print(f"\n{'='*70}")
        print("DETECTED ANSWERS (All 40 Questions)")
        print(f"{'='*70}")
        
        option_map = {1: "A", 2: "B", 3: "C", 4: "D"}
        
        # Show in two columns
        for row in range(20):
            q1 = row + 1
            q2 = row + 21
            
            # Question 1-20
            ans1 = answers.get(q1)
            conf1 = confidence.get(q1, 0)
            flag1 = f" [{flags[q1]}]" if q1 in flags else ""
            
            if ans1:
                result1 = f"Q{q1:2d}: {option_map[ans1]} ({conf1:3.0f}%){flag1}"
            else:
                result1 = f"Q{q1:2d}: (blank)"
            
            # Question 21-40
            ans2 = answers.get(q2)
            conf2 = confidence.get(q2, 0)
            flag2 = f" [{flags[q2]}]" if q2 in flags else ""
            
            if ans2:
                result2 = f"Q{q2:2d}: {option_map[ans2]} ({conf2:3.0f}%){flag2}"
            else:
                result2 = f"Q{q2:2d}: (blank)"
            
            print(f"  {result1:<35} {result2}")
        
        # Show raw intensity values for first 3 questions
        print(f"\n{'='*70}")
        print("RAW INTENSITY VALUES (Sample: Q1-Q3)")
        print(f"{'='*70}")
        print("(Lower values = darker marks)")
        
        for q in range(1, 4):
            if q in raw_results:
                intensities = raw_results[q]
                print(f"  Q{q}: A={intensities[1]:.0f}, B={intensities[2]:.0f}, "
                      f"C={intensities[3]:.0f}, D={intensities[4]:.0f}")
        
        # Show flagged questions
        if flags:
            print(f"\n{'='*70}")
            print(f"FLAGGED QUESTIONS ({len(flags)} total)")
            print(f"{'='*70}")
            
            flag_types = {}
            for q, flag_type in flags.items():
                if flag_type not in flag_types:
                    flag_types[flag_type] = []
                flag_types[flag_type].append(q)
            
            for flag_type, questions in sorted(flag_types.items()):
                print(f"\n  {flag_type}: {len(questions)} questions")
                print(f"    Questions: {', '.join(f'Q{q}' for q in sorted(questions))}")
        
        print(f"\n{'='*70}")
        print(f"💾 Debug image saved: debug_diagnostic.jpg")
        print(f"   View this image to see detected circles and grid")
        print(f"{'='*70}")
        
        return answers, flags, confidence
        
    except Exception as e:
        print(f"\n❌ Detection failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def compare_with_expected(answers, expected_str):
    """Compare detected answers with expected answers
    
    expected_str format: "1A,2B,3A,4A,5A..." or just "ABAAA..." for sequential
    """
    print(f"\n{'='*70}")
    print("COMPARISON WITH EXPECTED ANSWERS")
    print(f"{'='*70}")
    
    option_map = {"A": 1, "B": 2, "C": 3, "D": 4}
    reverse_map = {1: "A", 2: "B", 3: "C", 4: "D"}
    
    # Parse expected answers
    expected = {}
    if "," in expected_str:
        # Format: "1A,2B,3A..."
        for item in expected_str.split(","):
            item = item.strip()
            if len(item) >= 2:
                q_num = int(item[:-1])
                opt_letter = item[-1].upper()
                expected[q_num] = option_map.get(opt_letter)
    else:
        # Format: "ABAAA..." (sequential)
        for i, letter in enumerate(expected_str.upper()):
            if letter in option_map:
                expected[i + 1] = option_map[letter]
    
    # Compare
    correct = 0
    incorrect = 0
    missing = 0
    
    print(f"\nComparison Results:")
    print(f"{'Q':<4} {'Expected':<10} {'Detected':<10} {'Status'}")
    print("-" * 50)
    
    for q in range(1, 41):
        exp = expected.get(q)
        det = answers.get(q)
        
        if exp is None:
            continue
            
        exp_letter = reverse_map.get(exp, "?")
        det_letter = reverse_map.get(det, "?") if det else "blank"
        
        if det == exp:
            status = "✅ CORRECT"
            correct += 1
        elif det is None:
            status = "❌ MISSING"
            missing += 1
        else:
            status = "❌ WRONG"
            incorrect += 1
        
        if det != exp:
            print(f"Q{q:<2}  {exp_letter:<10} {det_letter:<10} {status}")
    
    total = len(expected)
    accuracy = (correct / total * 100) if total > 0 else 0
    
    print("\n" + "="*50)
    print(f"Accuracy: {correct}/{total} ({accuracy:.1f}%)")
    print(f"  Correct: {correct}")
    print(f"  Wrong: {incorrect}")
    print(f"  Missing: {missing}")
    print("="*50)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python diagnose_sheet.py <image_file>")
        print("  python diagnose_sheet.py <image_file> <expected_answers>")
        print("\nExample:")
        print("  python diagnose_sheet.py test_sheet.jpg")
        print("  python diagnose_sheet.py test_sheet.jpg DABAADAADCBBDABDAC...")
        print("  python diagnose_sheet.py test_sheet.jpg 1D,2A,3B,4A,5A...")
        sys.exit(1)
    
    img_path = sys.argv[1]
    answers, flags, confidence = analyze_image(img_path)
    
    # If expected answers provided, compare
    if len(sys.argv) >= 3 and answers:
        expected_str = sys.argv[2]
        compare_with_expected(answers, expected_str)
