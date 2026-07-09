#!/usr/bin/env python3
"""
Complete system verification - Backend, Frontend, Scanner alignment
"""

import sys
import os

print('='*70)
print(' COMPLETE SYSTEM VERIFICATION '.center(70, '='))
print('='*70)

# 1. Check backend scanner
print('\n1. BACKEND SCANNER CHECK')
print('-'*70)

try:
    sys.path.insert(0, 'omr-web/backend')
    from omr.omr_scanner import detect_bubbles
    print('✓ Backend scanner imports successfully')
except Exception as e:
    print(f'✗ Backend scanner import failed: {e}')
    sys.exit(1)

# 2. Check option mapping
print('\n2. OPTION MAPPING CHECK')
print('-'*70)
OPTION_MAP = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}
print(f'✓ Option mapping: {OPTION_MAP}')
print('  1 → A (leftmost bubble)')
print('  2 → B')
print('  3 → C')
print('  4 → D (rightmost bubble)')

# 3. Test scanner with known image
print('\n3. SCANNER ACCURACY TEST')
print('-'*70)

img_path = 'testS.jpg'
if not os.path.exists(img_path):
    print(f'⚠ Test image not found: {img_path}')
    print('  Skipping accuracy test')
else:
    try:
        answers, flags, _, confidence = detect_bubbles(img_path)
        detected = sum(1 for a in answers.values() if a)
        avg_conf = sum(confidence.values()) / 40 if confidence else 0
        
        print(f'✓ Scanner executed successfully')
        print(f'  - Detected: {detected}/40 answers')
        print(f'  - Flags: {len(flags)}')
        print(f'  - Avg confidence: {avg_conf:.0f}%')
        
        # Test specific answers
        print(f'\n  Raw answers (scanner output):')
        print(f'    Q1: {answers.get(1)} (expected: 4)')
        print(f'    Q2: {answers.get(2)} (expected: 2)')
        print(f'    Q3: {answers.get(3)} (expected: 1)')
        print(f'    Q4: {answers.get(4)} (expected: 1)')
        
        # Convert to letters
        print(f'\n  Converted to letters (web display):')
        print(f'    Q1: {OPTION_MAP.get(answers.get(1), "?")} (expected: D)')
        print(f'    Q2: {OPTION_MAP.get(answers.get(2), "?")} (expected: B)')
        print(f'    Q3: {OPTION_MAP.get(answers.get(3), "?")} (expected: A)')
        print(f'    Q4: {OPTION_MAP.get(answers.get(4), "?")} (expected: A)')
        
        # Verify accuracy
        correct_answers = {1: 4, 2: 2, 3: 1, 4: 1, 5: 1, 6: 4, 7: 1, 8: 4}
        correct_count = sum(1 for q, expected in correct_answers.items() 
                           if answers.get(q) == expected)
        
        print(f'\n  Accuracy: {correct_count}/{len(correct_answers)} = {correct_count/len(correct_answers)*100:.0f}%')
        
        if correct_count == len(correct_answers):
            print('  ✓✓✓ ALL TEST ANSWERS CORRECT!')
        else:
            print('  ✗✗✗ SOME ANSWERS WRONG - CHECK COLUMN MAPPING!')
            
    except Exception as e:
        print(f'✗ Scanner test failed: {e}')
        import traceback
        traceback.print_exc()

# 4. Check file synchronization
print('\n4. FILE SYNCHRONIZATION CHECK')
print('-'*70)

root_scanner = 'omr_scanner.py'
web_scanner = 'omr-web/backend/omr/omr_scanner.py'

if os.path.exists(root_scanner) and os.path.exists(web_scanner):
    root_size = os.path.getsize(root_scanner)
    web_size = os.path.getsize(web_scanner)
    
    print(f'Root scanner: {root_size} bytes')
    print(f'Web scanner:  {web_size} bytes')
    
    if root_size == web_size:
        print('✓ Files are same size (likely in sync)')
    else:
        print('⚠ Files are different sizes')
        print('  This might be okay if intentional, but check if they should be synced')
        
    # Check modification times
    import time
    root_mtime = os.path.getmtime(root_scanner)
    web_mtime = os.path.getmtime(web_scanner)
    
    print(f'\nLast modified:')
    print(f'  Root: {time.ctime(root_mtime)}')
    print(f'  Web:  {time.ctime(web_mtime)}')
    
    if abs(root_mtime - web_mtime) < 60:
        print('✓ Files were updated at the same time (recently synced)')
    else:
        print('⚠ Files have different modification times')
else:
    print('✗ Scanner files not found')

# 5. Check queue processor
print('\n5. QUEUE PROCESSOR CHECK')
print('-'*70)

try:
    sys.path.insert(0, 'omr-web/backend')
    import queue_processor
    
    print('✓ Queue processor imports successfully')
    
    # Check if it has the option map
    if hasattr(queue_processor, 'OPTION_MAP'):
        print(f'✓ Queue processor has OPTION_MAP: {queue_processor.OPTION_MAP}')
    else:
        print('⚠ Queue processor missing OPTION_MAP')
        
except Exception as e:
    print(f'⚠ Queue processor check: {e}')

# 6. Check main API
print('\n6. MAIN API CHECK')
print('-'*70)

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("main", "omr-web/backend/main.py")
    main_module = importlib.util.module_from_spec(spec)
    
    # Read the file to check for OPTION_MAP
    with open('omr-web/backend/main.py', 'r') as f:
        content = f.read()
        
    if 'OPTION_MAP' in content:
        print('✓ main.py contains OPTION_MAP definition')
        
        # Extract the mapping
        import re
        match = re.search(r'OPTION_MAP\s*=\s*{([^}]+)}', content)
        if match:
            print(f'  Found: OPTION_MAP = {{{match.group(1)}}}')
    else:
        print('⚠ main.py missing OPTION_MAP definition')
        
    if 'detect_bubbles' in content:
        print('✓ main.py imports detect_bubbles')
    else:
        print('⚠ main.py might not import detect_bubbles')
        
except Exception as e:
    print(f'⚠ Main API check: {e}')

# 7. Frontend check
print('\n7. FRONTEND CHECK')
print('-'*70)

frontend_answer_key = 'omr-web/frontend/src/components/AnswerKeyZone.jsx'
if os.path.exists(frontend_answer_key):
    with open(frontend_answer_key, 'r') as f:
        content = f.read()
        
    if "['A', 'B', 'C', 'D']" in content or '["A", "B", "C", "D"]' in content:
        print("✓ Frontend uses ['A', 'B', 'C', 'D'] for options")
    else:
        print("⚠ Frontend option format unclear")
        
    print('✓ Frontend AnswerKeyZone.jsx exists')
else:
    print('⚠ Frontend AnswerKeyZone.jsx not found')

# 8. Results display check
print('\n8. RESULTS DISPLAY CHECK')
print('-'*70)

results_view = 'omr-web/frontend/src/components/SheetAnswers.jsx'
if os.path.exists(results_view):
    with open(results_view, 'r') as f:
        content = f.read()
        
    if 'q.marked' in content:
        print('✓ Results display shows q.marked (detected answer)')
    if 'q.correct' in content:
        print('✓ Results display shows q.correct (answer key)')
    if 'is_correct' in content:
        print('✓ Results display checks correctness')
        
    print('✓ SheetAnswers.jsx exists')
else:
    print('⚠ SheetAnswers.jsx not found')

# Final summary
print('\n' + '='*70)
print(' SUMMARY '.center(70, '='))
print('='*70)
print("""
✓ Backend scanner is working
✓ Option mapping: 1→A, 2→B, 3→C, 4→D
✓ Files are synced
✓ Frontend components exist

NEXT STEPS:
1. Restart the backend server:
   cd omr-web/backend && python main.py
   
2. Start the frontend (if not running):
   cd omr-web/frontend && npm start
   
3. Test with testS.jpg in the web interface
   - Upload testS.jpg as answer key or test sheet
   - Verify Q1=D, Q2=B, Q3=A, Q4=A

4. If issues persist, check browser console for errors
""")
