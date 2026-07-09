#!/usr/bin/env python3
"""
Test the uploaded image against ground truth answers
"""

from omr_scanner import detect_bubbles

# Ground truth answers from the image
CORRECT_ANSWERS = {
    1: 4, 2: 2, 3: 1, 4: 1, 5: 1, 6: 4, 7: 1, 8: 4, 9: 3, 10: 3,
    11: 2, 12: 4, 13: 1, 14: 4, 15: 1, 16: 2, 17: 1, 18: 1, 19: 4, 20: 2,
    21: 3, 22: 3, 23: 3, 24: 4, 25: 3, 26: 4, 27: 1, 28: 1, 29: 3, 30: 4,
    31: 3, 32: 1, 33: 3, 34: 3, 35: 3, 36: 2, 37: 4, 38: 2, 39: 1, 40: 3
}

def test_image(image_path):
    """Test an image and compare with ground truth"""
    print("="*70)
    print(" TESTING UPLOADED IMAGE ".center(70, "="))
    print("="*70)
    
    # Detect answers
    answers, flags, raw_results, confidence = detect_bubbles(image_path, 'debug_uploaded_test.jpg')
    
    # Compare with ground truth
    correct_count = 0
    wrong_count = 0
    missed_count = 0
    
    print("\nQuestion-by-Question Comparison:")
    print("-"*70)
    print(f"{'Q#':<4} {'Correct':<8} {'Detected':<10} {'Confidence':<12} {'Status'}")
    print("-"*70)
    
    for q in range(1, 41):
        correct_ans = CORRECT_ANSWERS[q]
        detected_ans = answers.get(q)
        conf = confidence.get(q, 0)
        flag = flags.get(q, "")
        
        if detected_ans is None:
            status = "❌ MISSED"
            missed_count += 1
            color = ""
        elif detected_ans == correct_ans:
            status = "✅ CORRECT"
            correct_count += 1
            color = ""
        else:
            status = f"❌ WRONG"
            wrong_count += 1
            color = ""
        
        flag_str = f"[{flag}]" if flag else ""
        print(f"Q{q:<3} {correct_ans:<8} {detected_ans if detected_ans else 'None':<10} {conf:.0f}%{flag_str:<8} {status}")
    
    # Summary
    print("\n" + "="*70)
    print(" SUMMARY ".center(70, "="))
    print("="*70)
    print(f"Correct:       {correct_count}/40 ({correct_count/40*100:.1f}%)")
    print(f"Wrong:         {wrong_count}/40 ({wrong_count/40*100:.1f}%)")
    print(f"Missed:        {missed_count}/40 ({missed_count/40*100:.1f}%)")
    print(f"Total Flagged: {len(flags)}")
    
    # Show wrong answers in detail
    if wrong_count > 0:
        print("\n" + "="*70)
        print(" INCORRECT DETECTIONS ".center(70, "="))
        print("="*70)
        for q in range(1, 41):
            correct_ans = CORRECT_ANSWERS[q]
            detected_ans = answers.get(q)
            if detected_ans and detected_ans != correct_ans:
                conf = confidence.get(q, 0)
                flag = flags.get(q, "")
                print(f"Q{q}: Expected {correct_ans}, Got {detected_ans} "
                      f"(conf: {conf:.0f}%) {f'[{flag}]' if flag else ''}")
    
    print(f"\n💾 Debug image saved: debug_uploaded_test.jpg")
    
    return correct_count, wrong_count, missed_count

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_uploaded_image.py <image_path>")
        print("\nThis script tests the OMR scanner against known correct answers")
        sys.exit(1)
    
    test_image(sys.argv[1])
