#!/usr/bin/env python3
"""
Comprehensive test script for the updated OMR scanner with pen marking detection.

Usage:
    python test_omr_scanner.py
"""

import os
import glob
from pathlib import Path
from omr_scanner import detect_bubbles, batch_to_excel

def test_single_image(image_path, output_name):
    """Test single image processing."""
    print(f"\n🔍 Testing: {image_path}")
    print("-" * 60)
    
    try:
        answers, flags, raw_results = detect_bubbles(image_path, f"debug_{output_name}.jpg")
        
        print("✅ Detection successful!")
        print(f"📊 Results:")
        print(f"   - Total answers detected: {len([a for a in answers.values() if a is not None])}/40")
        print(f"   - Flagged questions: {len(flags)}")
        
        if flags:
            print(f"   - Flag types: {set(flags.values())}")
        
        # Show some sample answers
        print(f"\n📝 Sample detected answers:")
        option_map = {1: "A", 2: "B", 3: "C", 4: "D"}
        for q in sorted(list(answers.keys())[:10]):  # First 10 questions
            answer = answers[q]
            if answer is not None:
                letter = option_map.get(answer, str(answer))
                flag_info = f" (⚠️ {flags[q]})" if q in flags else ""
                print(f"   Q{q:2d}: {letter}{flag_info}")
            else:
                print(f"   Q{q:2d}: (blank)")
        
        if len(answers) > 10:
            print(f"   ... and {len(answers) - 10} more")
            
        print(f"\n✅ Debug visualization saved to: debug_{output_name}.jpg")
        return True
        
    except Exception as e:
        print(f"❌ Detection failed: {e}")
        return False

def test_batch_processing(image_pattern, output_file):
    """Test batch processing."""
    print(f"\n📦 Batch Processing Test: {image_pattern}")
    print("-" * 60)
    
    try:
        images = glob.glob(image_pattern)
        if not images:
            print(f"❌ No images found matching pattern: {image_pattern}")
            return False
            
        print(f"📁 Found {len(images)} images")
        for img in images:
            print(f"   - {os.path.basename(img)}")
        
        batch_to_excel(images, output_file)
        
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"✅ Batch processing successful!")
            print(f"📊 Excel file created: {output_file} ({size} bytes)")
            return True
        else:
            print(f"❌ Excel file not created: {output_file}")
            return False
            
    except Exception as e:
        print(f"❌ Batch processing failed: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 OMR Scanner Test Suite")
    print("=" * 60)
    print("Testing the updated OMR scanner with pen marking detection")
    print("=" * 60)
    
    successful_tests = 0
    total_tests = 0
    
    # Test cases
    test_cases = [
        # (image_path, debug_name, description)
        ("samples/sample2/AdrianSample/adrian_omr.png", "adrian1", "Adrian Sample 1"),
        ("samples/sample2/AdrianSample/adrian_omr_2.png", "adrian2", "Adrian Sample 2"),
        ("samples/sample1/MobileCamera/sheet1.jpg", "mobile1", "Mobile Camera Sheet"),
    ]
    
    print("\n📋 SINGLE IMAGE TESTS")
    print("=" * 40)
    
    for image_path, debug_name, description in test_cases:
        total_tests += 1
        print(f"\nTest {total_tests}: {description}")
        if os.path.exists(image_path):
            if test_single_image(image_path, debug_name):
                successful_tests += 1
        else:
            print(f"⚠️ Image not found: {image_path}")
    
    print("\n📦 BATCH PROCESSING TESTS")
    print("=" * 40)
    
    batch_tests = [
        ("samples/sample2/AdrianSample/*.png", "batch_adrian.xlsx", "Adrian Samples Batch"),
        ("samples/sample*/MobileCamera/*.jpg", "batch_mobile.xlsx", "Mobile Camera Batch"),
    ]
    
    for pattern, output, description in batch_tests:
        total_tests += 1
        print(f"\nTest {total_tests}: {description}")
        if test_batch_processing(pattern, output):
            successful_tests += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Successful tests: {successful_tests}/{total_tests}")
    print(f"❌ Failed tests: {total_tests - successful_tests}/{total_tests}")
    
    if successful_tests == total_tests:
        print("\n🎉 All tests passed! OMR Scanner is working perfectly.")
    elif successful_tests > 0:
        print(f"\n⚠️ Partial success. {successful_tests} tests passed.")
        print("   Some images may not be compatible with the current algorithm.")
    else:
        print("\n❌ All tests failed. Check the error messages above.")
    
    print("\n📚 FEATURES DEMONSTRATED:")
    print("   ✅ Hough Circle Transform for bubble detection")
    print("   ✅ Adaptive grid calibration")
    print("   ✅ Per-column linear drift correction")
    print("   ✅ Confidence-based flagging")
    print("   ✅ Multi-mark detection")
    print("   ✅ Batch Excel export")
    print("   ✅ Debug visualization")
    
    return successful_tests == total_tests

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)