#!/usr/bin/env python3
"""
Full OMR Scanner Test Suite Runner
Runs all available tests and generates a summary report
"""

import os
import sys
import subprocess
import json
from datetime import datetime

def run_command(cmd, description):
    """Run a command and capture output"""
    print(f"\n{'='*70}")
    print(f"Running: {description}")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        output = result.stdout
        if result.returncode != 0 and result.stderr:
            output += f"\n\nERROR OUTPUT:\n{result.stderr}"
        
        print(output)
        
        return {
            'success': result.returncode == 0,
            'output': output,
            'return_code': result.returncode
        }
    except subprocess.TimeoutExpired:
        print("⏱️  Test timed out after 5 minutes")
        return {
            'success': False,
            'output': 'Timeout',
            'return_code': -1
        }
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return {
            'success': False,
            'output': str(e),
            'return_code': -1
        }

def main():
    """Run all test suites"""
    print("="*70)
    print(" OMR SCANNER - FULL TEST SUITE ".center(70, "="))
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Test 1: Comprehensive Test Suite
    results['comprehensive'] = run_command(
        'python test_comprehensive.py',
        'Comprehensive Test Suite'
    )
    
    # Test 2: Original Test Suite  
    results['omr_scanner'] = run_command(
        'python test_omr_scanner.py',
        'Original OMR Scanner Tests'
    )
    
    # Test 3: Check debug outputs
    print(f"\n{'='*70}")
    print("Debug Image Summary")
    print(f"{'='*70}")
    
    debug_images = [f for f in os.listdir('.') if f.startswith('debug_') and f.endswith('.jpg')]
    print(f"\nGenerated {len(debug_images)} debug images:")
    for img in sorted(debug_images)[:10]:
        size = os.path.getsize(img) / 1024
        print(f"  - {img} ({size:.1f} KB)")
    if len(debug_images) > 10:
        print(f"  ... and {len(debug_images) - 10} more")
    
    # Test 4: Check Excel outputs
    print(f"\n{'='*70}")
    print("Excel Output Summary")
    print(f"{'='*70}")
    
    excel_files = [f for f in os.listdir('.') if f.startswith('batch_') and f.endswith('.xlsx')]
    print(f"\nGenerated {len(excel_files)} Excel files:")
    for xlsx in sorted(excel_files):
        size = os.path.getsize(xlsx) / 1024
        print(f"  - {xlsx} ({size:.1f} KB)")
    
    # Summary Report
    print(f"\n{'='*70}")
    print(" FINAL TEST SUMMARY ".center(70, "="))
    print(f"{'='*70}")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r['success'])
    
    print(f"\nTest Suites Run: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    print(f"\nDetailed Results:")
    for test_name, result in results.items():
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Exit with appropriate code
    sys.exit(0 if passed_tests == total_tests else 1)

if __name__ == "__main__":
    main()
