# How to Test Your OMR Image

## Step 1: Save the Image
Save your OMR sheet image to this directory with a name like:
```
test_mysheet.jpg
```

## Step 2: Run the Test
```bash
python test_uploaded_image.py test_mysheet.jpg
```

This will:
1. Scan the image
2. Compare detected answers with the correct answers (already entered in the script)
3. Show you exactly which questions are wrong
4. Generate a debug image showing what was detected

## Expected Correct Answers
The script has been pre-configured with these correct answers from your image:
- Q1: 4, Q2: 2, Q3: 1, Q4: 1, Q5: 1, Q6: 4, Q7: 1, Q8: 4, Q9: 3, Q10: 3
- Q11: 2, Q12: 4, Q13: 1, Q14: 4, Q15: 1, Q16: 2, Q17: 1, Q18: 1, Q19: 4, Q20: 2
- Q21: 3, Q22: 3, Q23: 3, Q24: 4, Q25: 3, Q26: 4, Q27: 1, Q28: 1, Q29: 3, Q30: 4
- Q31: 3, Q32: 1, Q33: 3, Q34: 3, Q35: 3, Q36: 2, Q37: 4, Q38: 2, Q39: 1, Q40: 3

## Alternative: Quick Test
If you just want to see what the scanner detects:
```bash
python quick_test.py -d test_mysheet.jpg
```

## Check Debug Image
After running the test, open `debug_uploaded_test.jpg` to see:
- Which circles were detected
- Which bubbles were considered filled
- The grid overlay

This will help diagnose any issues with detection.
