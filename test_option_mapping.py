#!/usr/bin/env python3
"""
Test different option mapping scenarios to find the issue
"""

from omr_scanner import detect_bubbles
import sys

# Ground truth for your image
CORRECT_ANSWERS = {
    1: 4, 2: 2, 3: 1, 4: 1, 5: 1, 6: 4, 7: 1, 8: 4, 9: 3, 10: 3,
    11: 2, 12: 4, 13: 1, 14: 4, 15: 1, 16: 2, 17: 1, 18: 1, 19: 4, 20: 2,
    21: 3, 22: 3, 23: 3, 24: 4, 25: 3, 26: 4, 27: 1, 28: 1, 29: 3, 30: 4,
    31: 3, 32: 1, 33: 3, 34: 3, 35: 3, 36: 2, 37: 4, 38: 2, 39: 1, 40: 3
}

def test_mapping(detected_answers, mapping, mapping_name):
    """Test a specific option mapping"""
    correct = 0
    for q, correct_ans in CORRECT_ANSWERS.items():
        detected = detected_answers.get(q)
        if detected:
            mapped = mapping.get(detected, detected)
            if mapped == correct_ans:
                correct += 1
    
    accuracy = correct / 40 * 100
    print(f"{mapping_name:30s}: {correct}/40 ({accuracy:.1f}%)")
    return accuracy

def find_correct_mapping(image_path):
    """Try different mappings to find which one matches ground truth"""
    
    print("="*70)
    print(" OPTION MAPPING DIAGNOSIS ".center(70, "="))
    print("="*70)
    
    # Detect answers with current scanner
    answers, _, _, _ = detect_bubbles(image_path)
    
    print(f"\nTesting different option mappings...\n")
    
    # Test different mapping scenarios
    mappings = {
        "Normal (1→1, 2→2, 3→3, 4→4)": {1: 1, 2: 2, 3: 3, 4: 4},
        "Reversed (1→4, 2→3, 3→2, 4→1)": {1: 4, 2: 3, 3: 2, 4: 1},
        "Shifted +1 (1→2, 2→3, 3→4, 4→1)": {1: 2, 2: 3, 3: 4, 4: 1},
        "Shifted -1 (1→4, 2→1, 3→2, 4→3)": {1: 4, 2: 1, 3: 2, 4: 3},
        "Swap 1↔2 (1→2, 2→1, 3→3, 4→4)": {1: 2, 2: 1, 3: 3, 4: 4},
        "Swap 3↔4 (1→1, 2→2, 3→4, 4→3)": {1: 1, 2: 2, 3: 4, 4: 3},
        "Swap 1↔3 (1→3, 2→2, 3→1, 4→4)": {1: 3, 2: 2, 3: 1, 4: 4},
        "Swap 2↔4 (1→1, 2→4, 3→3, 4→2)": {1: 1, 2: 4, 3: 3, 4: 2},
    }
    
    results = {}
    for name, mapping in mappings.items():
        accuracy = test_mapping(answers, mapping, name)
        results[name] = accuracy
    
    # Find best mapping
    best_mapping = max(results, key=results.get)
    best_accuracy = results[best_mapping]
    
    print("\n" + "="*70)
    if best_accuracy > 80:
        print(f"✅ FOUND IT! Best mapping: {best_mapping}")
        print(f"   Accuracy: {best_accuracy:.1f}%")
        print("\n📝 This means the scanner is detecting columns in this order:")
        mapping = mappings[best_mapping]
        print(f"   Physical column 1 → Option {mapping[1]}")
        print(f"   Physical column 2 → Option {mapping[2]}")
        print(f"   Physical column 3 → Option {mapping[3]}")
        print(f"   Physical column 4 → Option {mapping[4]}")
    else:
        print(f"⚠️  No clear mapping found. Best was {best_mapping} at {best_accuracy:.1f}%")
        print("   There may be a more complex issue with detection.")
    
    return best_mapping, mappings[best_mapping]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_option_mapping.py <image_path>")
        print("\nThis will test various column orderings to find the issue")
        sys.exit(1)
    
    find_correct_mapping(sys.argv[1])
