#!/usr/bin/env python3
"""
Test script for OMR Scanner v2.1
Tests the scanner on sample images and reports detailed results
"""

import os
import sys
from omr_scanner import detect_bubbles
import cv2

def test_single_image(image_path, expected_answers=None):
    """Test scanner on a single image"""
    print(f"\n{'='*70}")
    print(f"Testing: {image_path}")
    print(f"{'='*70}")
    
    if not os.path.exists(image_path):
        print(f"❌ ERROR: File not found: {image_path}")
        return None
    
    try:
        # Generate debug output path
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        debug_out = f"debug_{base_name}.jpg"
        
        # Run scanner
        answers, flags, raw_data, confidence = detect_bubbles(image_path, debug_out)
        
        # Calculate statistics
        total_answered = sum(1 for a in answers.values() if a is not None)
        total_uncertain = sum(1 for f in flags.values() if f in ['no_clear_mark', 'low_confidence'])
        total_multi = sum(1 for f in flags.values() if f == 'multi_mark')
        total_smudged = sum(1 for f in flags.values() if f == 'row_smudged')
        avg_conf = sum(confidence.values()) / 40 if confidence else 0
        
        print(f"\n📊 RESULTS:")
        print(f"   Answered: {total_answered}/40")
        print(f"   Uncertain: {total_uncertain}")
        print(f"   Multi-marks: {total_multi}")
        print(f"   Smudged: {total_smudged}")
        print(f"   Avg Confidence: {avg_conf:.1f}%")
        
        # Show answers with confidence
        print(f"\n📝 ANSWERS:")
        for q in range(1, 41):
            ans = answers.get(q)
            conf = confidence.get(q, 0)
            flag = flags.get(q, "")
            
            if ans is not None:
                if conf >= 85:
                    status = "🟢"
                elif conf >= 70:
                    status = "🟡"
                elif conf >= 55:
                    status = "🟠"
                else:
                    status = "🔴"
                print(f"   Q{q:2d}: {status} Option {ans} ({conf:3.0f}% confidence)")
            else:
                print(f"   Q{q:2d}: ❌ NO ANSWER ({flag})")
        
        # Show warnings
        if total_uncertain + total_multi + total_smudged > 0:
            print(f"\n⚠️  WARNINGS:")
            for q in sorted(flags.keys()):
                if flags[q] in ['low_confidence', 'multi_mark', 'row_smudged']:
                    print(f"   Q{q}: {flags[q]}")
        
        # Compare with expected answers if provided
        if expected_answers:
            correct = sum(1 for q, expected in expected_answers.items() 
                         if answers.get(q) == expected)
            total_expected = len(expected_answers)
            accuracy = (correct / total_expected * 100) if total_expected > 0 else 0
            
            print(f"\n✅ ACCURACY: {correct}/{total_expected} ({accuracy:.1f}%)")
            
            # Show incorrect answers
            incorrect = [q for q, expected in expected_answers.items() 
                        if answers.get(q) != expected]
            if incorrect:
                print(f"\n❌ INCORRECT ANSWERS:")
                for q in incorrect:
                    detected = answers.get(q, "None")
                    expected = expected_answers[q]
                    conf = confidence.get(q, 0)
                    print(f"   Q{q}: Detected {detected}, Expected {expected} (conf: {conf:.0f}%)")
        
        print(f"\n💾 Debug image saved: {debug_out}")
        
        return {
            'answers': answers,
            'flags': flags,
            'confidence': confidence,
            'total_answered': total_answered,
            'avg_confidence': avg_conf
        }
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_batch(image_folder):
    """Test scanner on all images in a folder"""
    print(f"\n{'#'*70}")
    print(f"# BATCH TEST: {image_folder}")
    print(f"{'#'*70}")
    
    if not os.path.exists(image_folder):
        print(f"❌ ERROR: Folder not found: {image_folder}")
        return
    
    # Find all image files
    image_files = []
    for filename in os.listdir(image_folder):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            image_files.append(os.path.join(image_folder, filename))
    
    if not image_files:
        print(f"❌ No images found in {image_folder}")
        return
    
    print(f"\nFound {len(image_files)} images")
    
    # Test each image
    results = []
    for img_path in sorted(image_files):
        result = test_single_image(img_path)
        if result:
            results.append(result)
    
    # Summary
    if results:
        print(f"\n{'='*70}")
        print(f"SUMMARY")
        print(f"{'='*70}")
        
        avg_answered = sum(r['total_answered'] for r in results) / len(results)
        avg_confidence_overall = sum(r['avg_confidence'] for r in results) / len(results)
        
        print(f"   Total images processed: {len(results)}")
        print(f"   Average answered: {avg_answered:.1f}/40")
        print(f"   Average confidence: {avg_confidence_overall:.1f}%")
        
        # Confidence distribution
        high_conf_count = sum(1 for r in results if r['avg_confidence'] >= 80)
        med_conf_count = sum(1 for r in results if 60 <= r['avg_confidence'] < 80)
        low_conf_count = sum(1 for r in results if r['avg_confidence'] < 60)
        
        print(f"\n   Confidence Distribution:")
        print(f"      High (≥80%): {high_conf_count} images")
        print(f"      Medium (60-79%): {med_conf_count} images")
        print(f"      Low (<60%): {low_conf_count} images")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_scanner.py <image_file>          - Test single image")
        print("  python test_scanner.py <image_folder>        - Test all images in folder")
        print("\nExample:")
        print("  python test_scanner.py sample1.jpg")
        print("  python test_scanner.py ./samples/")
        sys.exit(1)
    
    path = sys.argv[1]
    
    if os.path.isfile(path):
        # Single image test
        test_single_image(path)
    elif os.path.isdir(path):
        # Batch test
        test_batch(path)
    else:
        print(f"❌ ERROR: Not found: {path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
