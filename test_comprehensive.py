#!/usr/bin/env python3
"""
Comprehensive OMR Scanner Test Suite
Tests scanner accuracy, robustness, and edge cases
"""

import os
import sys
import glob
import json
from pathlib import Path
from omr_scanner import detect_bubbles, batch_to_excel
import cv2
import numpy as np

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")

def print_section(text):
    print(f"\n{Colors.BOLD}{text}{Colors.END}")
    print("-" * 70)

def get_image_info(img_path):
    """Get basic image information"""
    img = cv2.imread(img_path)
    if img is None:
        return None
    h, w = img.shape[:2]
    return {
        'width': w,
        'height': h,
        'aspect_ratio': w / h,
        'size_mb': os.path.getsize(img_path) / (1024 * 1024)
    }

def test_single_image(img_path, test_name="", expected_answers=None):
    """Test a single image and return detailed results"""
    print_section(f"Test: {test_name or os.path.basename(img_path)}")
    
    if not os.path.exists(img_path):
        print(f"{Colors.RED}✗ File not found: {img_path}{Colors.END}")
        return None
    
    # Image info
    info = get_image_info(img_path)
    if info:
        print(f"Image: {info['width']}x{info['height']} "
              f"(aspect: {info['aspect_ratio']:.2f}, "
              f"size: {info['size_mb']:.2f}MB)")
    
    # Run detection
    try:
        debug_name = f"debug_{test_name.replace(' ', '_')}.jpg" if test_name else None
        answers, flags, raw_results, confidence = detect_bubbles(img_path, debug_name)
        
        # Calculate metrics
        total_questions = 40
        answered = sum(1 for a in answers.values() if a is not None)
        blank = total_questions - answered
        flagged = len(flags)
        avg_conf = np.mean([confidence.get(q, 0) for q in range(1, 41)])
        
        # Confidence distribution
        high_conf = sum(1 for q in range(1, 41) if confidence.get(q, 0) >= 80)
        med_conf = sum(1 for q in range(1, 41) if 60 <= confidence.get(q, 0) < 80)
        low_conf = sum(1 for q in range(1, 41) if 0 < confidence.get(q, 0) < 60)
        
        # Print results
        print(f"\n{Colors.GREEN}✓ Detection successful{Colors.END}")
        print(f"\nMetrics:")
        print(f"  Answered:      {answered}/{total_questions} ({answered/total_questions*100:.1f}%)")
        print(f"  Blank:         {blank}")
        print(f"  Flagged:       {flagged}")
        print(f"  Avg Confidence: {avg_conf:.1f}%")
        print(f"\nConfidence Distribution:")
        print(f"  High (≥80%):   {high_conf}")
        print(f"  Medium (60-79%): {med_conf}")
        print(f"  Low (<60%):    {low_conf}")
        
        # Flag types
        if flags:
            flag_types = {}
            for flag_type in flags.values():
                flag_types[flag_type] = flag_types.get(flag_type, 0) + 1
            print(f"\nFlag Types:")
            for flag_type, count in sorted(flag_types.items()):
                print(f"  {flag_type}: {count}")
        
        # Compare with expected answers
        accuracy = None
        if expected_answers:
            correct = sum(1 for q, expected in expected_answers.items() 
                         if answers.get(q) == expected)
            total_expected = len(expected_answers)
            accuracy = correct / total_expected * 100 if total_expected > 0 else 0
            print(f"\n{Colors.BOLD}Accuracy: {correct}/{total_expected} ({accuracy:.1f}%){Colors.END}")
            
            # Show errors
            errors = [(q, answers.get(q), expected) 
                     for q, expected in expected_answers.items() 
                     if answers.get(q) != expected]
            if errors and len(errors) <= 10:
                print(f"\nErrors:")
                for q, detected, expected in errors:
                    print(f"  Q{q}: detected {detected}, expected {expected}")
            elif len(errors) > 10:
                print(f"\n{len(errors)} errors (too many to display)")
        
        if debug_name:
            print(f"\n{Colors.BLUE}Debug image: {debug_name}{Colors.END}")
        
        return {
            'success': True,
            'answered': answered,
            'blank': blank,
            'flagged': flagged,
            'avg_confidence': avg_conf,
            'accuracy': accuracy,
            'answers': answers,
            'flags': flags,
            'confidence': confidence
        }
        
    except Exception as e:
        print(f"{Colors.RED}✗ Detection failed: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

def test_batch(image_pattern, test_name=""):
    """Test a batch of images"""
    print_section(f"Batch Test: {test_name}")
    
    images = glob.glob(image_pattern)
    if not images:
        print(f"{Colors.RED}✗ No images found matching: {image_pattern}{Colors.END}")
        return None
    
    print(f"Found {len(images)} images")
    
    results = []
    for img_path in sorted(images):
        print(f"\n  Testing: {os.path.basename(img_path)}", end=" ... ")
        try:
            answers, flags, _, confidence = detect_bubbles(img_path)
            answered = sum(1 for a in answers.values() if a is not None)
            avg_conf = np.mean([confidence.get(q, 0) for q in range(1, 41)])
            print(f"{Colors.GREEN}OK{Colors.END} "
                  f"(answered: {answered}/40, conf: {avg_conf:.0f}%)")
            results.append({
                'success': True,
                'answered': answered,
                'avg_confidence': avg_conf,
                'flagged': len(flags)
            })
        except Exception as e:
            print(f"{Colors.RED}FAILED{Colors.END} ({str(e)[:50]})")
            results.append({'success': False, 'error': str(e)})
    
    # Summary
    successful = sum(1 for r in results if r.get('success'))
    print(f"\n{Colors.BOLD}Summary:{Colors.END}")
    print(f"  Successful: {successful}/{len(results)}")
    if successful > 0:
        successful_results = [r for r in results if r.get('success')]
        avg_answered = np.mean([r['answered'] for r in successful_results])
        avg_conf = np.mean([r['avg_confidence'] for r in successful_results])
        print(f"  Avg Answered: {avg_answered:.1f}/40")
        print(f"  Avg Confidence: {avg_conf:.1f}%")
    
    return results

def run_all_tests():
    """Run all test suites"""
    print_header("OMR Scanner Comprehensive Test Suite")
    
    all_results = {}
    
    # Test Suite 1: Individual Sample Tests
    print_header("Test Suite 1: Individual Samples")
    
    test_cases = [
        {
            'name': 'Sample 6 - Doc Scan 1',
            'path': 'samples/sample6/doc-scans/sample_roll_01.jpg'
        },
        {
            'name': 'Sample 6 - Doc Scan 2',
            'path': 'samples/sample6/doc-scans/sample_roll_02.jpg'
        },
        {
            'name': 'Sample 4 - Mobile Photo 1',
            'path': 'samples/sample4/IMG_20201116_143512.jpg'
        },
        {
            'name': 'Sample 5 - CamScanner 1',
            'path': 'samples/sample5/ScanBatch1/camscanner-1.jpg'
        },
    ]
    
    for test_case in test_cases:
        if os.path.exists(test_case['path']):
            result = test_single_image(test_case['path'], test_case['name'])
            all_results[test_case['name']] = result
    
    # Test Suite 2: Batch Processing
    print_header("Test Suite 2: Batch Processing")
    
    batch_tests = [
        {
            'name': 'Sample 6 - All Doc Scans',
            'pattern': 'samples/sample6/doc-scans/*.jpg'
        },
        {
            'name': 'Sample 5 - Batch 1',
            'pattern': 'samples/sample5/ScanBatch1/*.jpg'
        },
    ]
    
    for batch_test in batch_tests:
        result = test_batch(batch_test['pattern'], batch_test['name'])
        all_results[f"batch_{batch_test['name']}"] = result
    
    # Final Summary
    print_header("Final Summary")
    
    successful_tests = 0
    for r in all_results.values():
        if r:
            if isinstance(r, dict) and r.get('success'):
                successful_tests += 1
            elif isinstance(r, list) and any(x.get('success', False) for x in r):
                successful_tests += 1
    total_tests = len(all_results)
    
    print(f"Total Test Suites: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {total_tests - successful_tests}")
    
    # Accuracy by test
    print(f"\n{Colors.BOLD}Test Results:{Colors.END}")
    for name, result in all_results.items():
        if result:
            if isinstance(result, dict) and result.get('success'):
                status = f"{Colors.GREEN}✓{Colors.END}"
                details = f"answered: {result.get('answered', 0)}/40, "
                details += f"conf: {result.get('avg_confidence', 0):.0f}%"
                if result.get('accuracy'):
                    details += f", accuracy: {result.get('accuracy'):.1f}%"
                print(f"  {status} {name}: {details}")
            elif isinstance(result, list):
                successful = sum(1 for r in result if r.get('success'))
                status = f"{Colors.GREEN}✓{Colors.END}" if successful > 0 else f"{Colors.RED}✗{Colors.END}"
                print(f"  {status} {name}: {successful}/{len(result)} passed")
            else:
                print(f"  {Colors.RED}✗{Colors.END} {name}: {result.get('error', 'unknown error')[:50]}")
    
    return all_results

if __name__ == "__main__":
    run_all_tests()
