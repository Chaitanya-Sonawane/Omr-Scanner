# 🧪 OMR Scanner - Testing Guide

## Quick Start Testing

### Prerequisites
```bash
cd omr-scanner-ui-redesign
npm install
npm run dev
```

Open: http://localhost:3000

---

## 🎯 Feature Testing Checklist

### 1. Header & Settings Panel

#### Test: Settings Panel Opens/Closes
- [ ] Click Settings icon in header
- [ ] Panel slides in from right with backdrop
- [ ] Click backdrop → Panel closes
- [ ] Click X button → Panel closes

#### Test: Settings Functionality
- [ ] Change passing score (0-40) → Updates live
- [ ] Toggle dark mode → Theme changes smoothly
- [ ] Toggle auto-export → Switch animates
- [ ] Toggle notifications → Switch animates
- [ ] Click "Save Settings" → Panel closes + settings persist

#### Test: Dark Mode
- [ ] Open settings → Toggle dark mode ON
- [ ] Verify all colors update correctly
- [ ] Reload page → Dark mode persists
- [ ] Toggle OFF → Back to light mode

**Expected**: Smooth transitions, no flashing, colors adjust properly

---

### 2. Answer Key Setup (Step 1)

#### Test: Manual Entry
- [ ] Click "Manual Entry" tab
- [ ] Fill in some answers (A, B, C, D)
- [ ] Leave some blank
- [ ] Click "Confirm Answer Key"
- [ ] Step indicator updates → Step 1 complete

**Expected**: Green checkmark on Step 1, proceeds to Step 2

---

### 3. Sheet Upload (Step 2)

#### Test: Drag & Drop Animation
- [ ] Drag a file over the drop zone
- [ ] Verify zone scales up + pulse animation
- [ ] Drop file → File appears in list
- [ ] Verify staggered slide-in animation for files

#### Test: File Management
- [ ] Click drop zone → File picker opens
- [ ] Select multiple files
- [ ] Files appear with names and sizes
- [ ] Hover over remove (X) button → Scale animation
- [ ] Click remove → File disappears
- [ ] Add more files → Animations repeat

**Expected**: Smooth animations, no lag, files list correctly

---

### 4. Processing (Step 3)

#### Test: Real-time Progress
- [ ] After uploading sheets, processing starts automatically
- [ ] Each sheet shows:
  - "Queued" status initially
  - "Processing" with animated progress bar
  - "Done" with green checkmark
- [ ] Progress bars fill smoothly (0-100%)
- [ ] Summary updates in real-time

**Expected**: Smooth progress animations, accurate status updates

---

### 5. Results (Step 4)

#### Test: Statistics Dashboard
- [ ] Verify 6 stat cards displayed
- [ ] Hover over each card → Lift effect + shadow
- [ ] Check values are accurate:
  - Total Students
  - Average Score
  - Pass Rate
  - Highest Score
  - Lowest Score
  - At Risk count

#### Test: Charts Toggle
- [ ] Click "Show Analytics" → Charts appear with fade-in
- [ ] Verify bar chart shows distribution:
  - Excellent (green)
  - Good (blue)
  - Average (yellow)
  - Below Avg (red)
- [ ] Bars animate on load
- [ ] Click "Hide Analytics" → Charts disappear

#### Test: Search & Filter
- [ ] Type in search bar → Results filter instantly
- [ ] Try searching by:
  - Student name
  - Student ID
- [ ] Verify result count updates: "Showing X of Y results"
- [ ] Clear search → All results return
- [ ] Change sort: Score → Name → Results reorder
- [ ] Filter by "Pass" → Only passing students shown
- [ ] Filter by "Fail" → Only failing students shown
- [ ] Filter by "All" → All students shown

**Expected**: Instant filtering, no lag, accurate counts

#### Test: Quick Actions
- [ ] Click "Export CSV" → File downloads
- [ ] Open CSV → Verify data is correct
- [ ] Click "Print" → Print dialog opens
- [ ] Verify print preview looks clean
- [ ] Click "Refresh" → Page reloads

#### Test: Results Table (Desktop)
- [ ] Scroll down to table
- [ ] Hover over row → Border color changes
- [ ] Click chevron → Row expands
- [ ] Verify answer details shown:
  - Green for correct
  - Red for incorrect
  - Yellow for unanswered
- [ ] Click chevron again → Row collapses

#### Test: Results Cards (Mobile)
- [ ] Resize browser to < 768px
- [ ] Verify card layout appears
- [ ] Tap "Show Answer Details" → Expands
- [ ] Scroll within expanded answers
- [ ] Tap "Hide Answer Details" → Collapses

**Expected**: Smooth animations, clean layout, accurate data

---

### 6. Export Functionality

#### Test: CSV Export
- [ ] Click "Excel" button in Quick Actions
- [ ] File downloads as `omr-results-YYYY-MM-DD.csv`
- [ ] Open in Excel/Google Sheets
- [ ] Verify columns:
  - Student ID
  - Name
  - Total Score
  - Intelligence
  - Science
  - Social
  - Math
- [ ] Verify all rows present and accurate

#### Test: Print/PDF
- [ ] Click "Print" button
- [ ] Print dialog opens
- [ ] Select "Save as PDF" (or print preview)
- [ ] Verify layout is clean:
  - No cut-off content
  - Proper margins
  - Readable fonts
- [ ] Save PDF → Verify file looks professional

**Expected**: Clean exports, accurate data, professional formatting

---

### 7. Responsive Design

#### Test: Desktop (> 1024px)
- [ ] Verify 3-4 column stat grid
- [ ] Table view for results
- [ ] Horizontal progress tracker
- [ ] All features visible

#### Test: Tablet (768px - 1024px)
- [ ] Verify 2-3 column stat grid
- [ ] Table still visible
- [ ] Horizontal progress tracker
- [ ] Buttons show icons + text

#### Test: Mobile (< 768px)
- [ ] Verify 1-2 column layout
- [ ] Card view for results
- [ ] Vertical progress tracker
- [ ] Buttons show icons only
- [ ] Touch targets are large enough (44×44px)
- [ ] No horizontal scroll on content

**Browser Resize Test**:
1. Start at 1920px width
2. Slowly resize down to 375px
3. Verify no layout breaks
4. Check all features still accessible

---

### 8. Animations & Micro-interactions

#### Test: Settings Panel Animation
- [ ] Open settings → Slides in from right (300ms)
- [ ] Backdrop fades in (200ms)
- [ ] Close → Reverses smoothly

#### Test: Drag & Drop Animations
- [ ] Hover → Zone scales to 1.01x
- [ ] Drag active → Scales to 1.02x + pulse
- [ ] Files appear → Staggered slide-in (50ms delay each)

#### Test: Card Hover Effects
- [ ] Hover stat cards → Lift + shadow
- [ ] Hover result rows → Border color change
- [ ] Hover buttons → Scale/color change

#### Test: Progress Animations
- [ ] Progress bars fill smoothly
- [ ] Spinner rotates continuously
- [ ] Status badges update with transitions

**Expected**: All animations smooth, no janky movements

---

### 9. Accessibility Testing

#### Test: Keyboard Navigation
- [ ] Tab through all interactive elements
- [ ] Verify focus visible (blue outline)
- [ ] Press Enter/Space on buttons → Activates
- [ ] Press Escape in settings panel → Closes
- [ ] Arrow keys work in dropdowns

#### Test: Screen Reader (Optional)
- [ ] Turn on screen reader (NVDA/VoiceOver)
- [ ] Navigate through page
- [ ] Verify all elements are announced
- [ ] Buttons have proper labels
- [ ] Images have alt text

#### Test: Color Contrast
- [ ] Use browser DevTools accessibility checker
- [ ] Verify all text has 4.5:1 contrast minimum
- [ ] Check in both light and dark modes

**Expected**: All elements accessible, proper focus management

---

### 10. Performance Testing

#### Test: Load Time
- [ ] Clear cache
- [ ] Reload page
- [ ] Open DevTools → Network tab
- [ ] Verify total load < 2 seconds
- [ ] Check bundle sizes:
  - Main JS: ~45KB gzipped
  - CSS: ~27KB gzipped

#### Test: Animation Performance
- [ ] Open DevTools → Performance tab
- [ ] Record while:
  - Opening settings panel
  - Expanding result rows
  - Dragging files
- [ ] Check FPS stays above 60

#### Test: Memory Leaks
- [ ] Open DevTools → Memory tab
- [ ] Take heap snapshot
- [ ] Process 100 sheets
- [ ] Take another snapshot
- [ ] Verify memory doesn't grow excessively

**Expected**: Fast load, smooth 60fps, no memory leaks

---

## 🐛 Known Issues (None Currently)

If you find any issues during testing, document:
1. Steps to reproduce
2. Expected behavior
3. Actual behavior
4. Browser/device
5. Screenshots/videos

---

## ✅ Pre-Deployment Checklist

Before deploying to production:

### Functionality
- [ ] All 4 steps work correctly
- [ ] Search and filters function properly
- [ ] Export CSV downloads correctly
- [ ] Print layout is clean
- [ ] Settings persist across sessions
- [ ] Dark mode works in all components

### Visual
- [ ] No layout breaks at any screen size
- [ ] All animations are smooth
- [ ] Colors are consistent
- [ ] Typography is readable
- [ ] Icons are aligned

### Performance
- [ ] Lighthouse score > 90
- [ ] No console errors
- [ ] No console warnings
- [ ] Bundle size is acceptable
- [ ] Images are optimized

### Accessibility
- [ ] Keyboard navigation works
- [ ] Focus indicators visible
- [ ] Color contrast passes WCAG AA
- [ ] ARIA labels present
- [ ] Screen reader friendly

### Cross-Browser
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

### Cross-Device
- [ ] Desktop (1920×1080)
- [ ] Laptop (1440×900)
- [ ] Tablet (768×1024)
- [ ] Mobile (375×667)

---

## 🔧 Debugging Tips

### Issue: Animations not working
**Solution**: Check if browser supports CSS animations
```js
// In browser console
console.log(window.CSS.supports('animation', 'fade-in'))
```

### Issue: Dark mode not persisting
**Solution**: Check localStorage
```js
// In browser console
localStorage.getItem('omr-settings')
```

### Issue: Export not working
**Solution**: Check browser console for errors
```js
// Look for CORS or blob URL errors
```

### Issue: Layout breaks on resize
**Solution**: Check for fixed widths in CSS
```css
/* Avoid: width: 500px */
/* Use: width: 100%; max-width: 500px */
```

---

## 📊 Testing Results Template

Use this template to document testing:

```
Date: ___________
Tester: __________
Browser: __________
Device: __________

✅ Header & Settings Panel
✅ Answer Key Setup
✅ Sheet Upload
✅ Processing
✅ Results Display
✅ Search & Filter
✅ Export Functionality
✅ Responsive Design
✅ Animations
✅ Accessibility

Issues Found: _________
Severity: _________
Status: _________
```

---

## 🎉 Testing Complete!

If all tests pass:
1. ✅ Mark as production-ready
2. ✅ Deploy to staging
3. ✅ User acceptance testing
4. ✅ Deploy to production

**Happy Testing!** 🚀
