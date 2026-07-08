# ⚡ Quick Start Guide - OMR Scanner

## 🚀 Get Up and Running in 5 Minutes

---

## Prerequisites

- Node.js 18+ installed
- npm or pnpm package manager
- A modern browser (Chrome, Firefox, Safari, Edge)

---

## 1️⃣ Installation

```bash
# Navigate to project
cd omr-scanner-ui-redesign

# Install dependencies
npm install

# Start development server
npm run dev
```

**Expected output**:
```
✓ Ready in 1599ms
- Local:   http://localhost:3000
```

---

## 2️⃣ Open in Browser

Visit: **http://localhost:3000**

You should see:
- Clean header with "OMR Scanner" logo
- Step indicator showing 4 steps
- Answer Key Setup form (Step 1)

---

## 3️⃣ Quick Demo (5 steps)

### Step 1: Set Answer Key
1. Click **"Manual Entry"** tab
2. Click random letters (A, B, C, D) for 40 questions
3. Click **"Confirm Answer Key"** button
4. ✅ Step 1 turns green, Step 2 appears

### Step 2: Upload Sheets
1. Scroll down to "Upload Sheets" section
2. Click the upload zone (or drag files)
3. Select any image files from your computer
4. Files appear in list below
5. Processing starts automatically

### Step 3: Watch Processing
1. See progress bars fill for each sheet
2. Status changes: Queued → Processing → Done
3. Takes ~30 seconds for demo simulation

### Step 4: View Results
1. Results table appears automatically
2. See statistics dashboard
3. Try clicking **"Show Analytics"** button
4. Use search bar to find students
5. Click **"Export CSV"** to download

---

## 4️⃣ Try New Features

### Settings Panel
1. Click **Settings icon** (⚙️) in header
2. Panel slides in from right
3. Try toggling **Dark Mode**
4. Change **Passing Score** to 25
5. Click **"Save Settings"**

### Search & Filter
1. In Results step, type in search bar
2. Try sorting by name
3. Filter by "Pass" or "Fail"
4. Watch results update instantly

### Export Functions
1. Click **"Excel"** button → CSV downloads
2. Click **"Print"** button → Print dialog opens
3. Save as PDF if you want

### Interactive Charts
1. Click **"Show Analytics"** button
2. See score distribution chart
3. Hover over stat cards
4. Click **"Hide Analytics"** to toggle off

---

## 5️⃣ Explore Code

### Main Files
```
app/page.tsx              ← Main app logic
components/omr/           ← All UI components
  ├── Header.tsx          ← Top navigation
  ├── SettingsPanel.tsx   ← Settings modal
  ├── steps/
  │   └── ResultsStep.tsx ← Results display
  └── StatisticsDashboard.tsx ← Stats cards
hooks/useOMRState.ts      ← State management
app/globals.css           ← Styles & animations
```

### Edit Something

**Try this**: Change the app title

1. Open `components/omr/Header.tsx`
2. Find line: `<h1 className="text-lg font-bold text-foreground">OMR Scanner</h1>`
3. Change to: `<h1 className="text-lg font-bold text-foreground">My OMR App</h1>`
4. Save file → Browser auto-refreshes
5. See your change instantly!

---

## 🎨 Customize

### Change Primary Color

Edit `app/globals.css`:
```css
:root {
  --primary: oklch(0.45 0.25 270); /* Blue */
}
```

Change to red:
```css
:root {
  --primary: oklch(0.58 0.25 25); /* Red */
}
```

Save → All primary colors update!

### Change Passing Score Default

Edit `components/omr/SettingsPanel.tsx`:
```tsx
const [passingScore, setPassingScore] = useState(20);
```

Change to:
```tsx
const [passingScore, setPassingScore] = useState(24);
```

---

## 📖 Documentation

### Learn More
- **[README.md](./README.md)** - Project overview
- **[FEATURE_SHOWCASE.md](./FEATURE_SHOWCASE.md)** - Feature details
- **[COMPONENT_HIERARCHY.md](./COMPONENT_HIERARCHY.md)** - Code structure
- **[UI_ENHANCEMENTS.md](./UI_ENHANCEMENTS.md)** - Technical docs
- **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** - How to test

---

## 🐛 Common Issues

### Issue: Port 3000 already in use
```bash
# Kill existing process
npx kill-port 3000

# Or use different port
npm run dev -- -p 3001
```

### Issue: Dark mode not working
- Check browser console for errors
- Try clearing localStorage:
```js
// In browser console
localStorage.clear()
```

### Issue: Animations not smooth
- Check if running on low-end device
- Try closing other tabs
- Check CPU usage

### Issue: Export not working
- Check browser console for errors
- Try different browser
- Verify popup blockers aren't active

---

## 🎓 Learning Path

### Beginner
1. ✅ Run the app locally
2. ✅ Navigate through 4 steps
3. ✅ Try all features
4. ✅ Read README.md
5. ✅ Customize colors

### Intermediate
1. Read COMPONENT_HIERARCHY.md
2. Understand data flow
3. Modify a component
4. Add a new stat card
5. Create a new animation

### Advanced
1. Add backend integration
2. Implement real OCR
3. Add user authentication
4. Deploy to production
5. Scale for thousands of users

---

## 🔥 Pro Tips

### Hot Module Replacement (HMR)
- Edit files while server is running
- Changes appear instantly
- State is preserved

### DevTools
```bash
# Open browser DevTools
Mac: Cmd + Option + I
Windows/Linux: F12 or Ctrl + Shift + I
```

### Responsive Design Testing
```bash
# In DevTools
1. Toggle device toolbar (Cmd/Ctrl + Shift + M)
2. Select iPhone, iPad, etc.
3. Test at different sizes
```

### Performance Profiling
```bash
# In DevTools → Performance tab
1. Click Record
2. Interact with app
3. Stop recording
4. Analyze FPS and timings
```

---

## 🚢 Deploy to Production

### Build for Production
```bash
npm run build
```

### Test Production Build Locally
```bash
npm run start
# → http://localhost:3000
```

### Deploy Options

**Vercel** (Recommended):
```bash
npm install -g vercel
vercel deploy
```

**Netlify**:
```bash
npm run build
# Upload .next folder to Netlify
```

**Self-Hosted**:
```bash
npm run build
npm run start
# Or use PM2, Docker, etc.
```

---

## 📊 Success Checklist

### After 5 Minutes
- [ ] App running on localhost:3000
- [ ] Navigated through all 4 steps
- [ ] Processed sample sheets
- [ ] Viewed results

### After 30 Minutes
- [ ] Tried all new features
- [ ] Toggled dark mode
- [ ] Exported CSV
- [ ] Used search and filters
- [ ] Read key documentation

### After 1 Hour
- [ ] Customized a color
- [ ] Modified a component
- [ ] Tested responsiveness
- [ ] Explored code structure

---

## 🆘 Need Help?

### Resources
- 📚 **Documentation**: See docs in project root
- 🐛 **Issues**: Check browser console first
- 💬 **Questions**: Review FAQ in README
- 🔍 **Code**: Read inline comments

### Troubleshooting Steps
1. Clear browser cache
2. Delete `node_modules` and reinstall
3. Check Node.js version (18+)
4. Try different browser
5. Check network tab in DevTools

---

## 🎉 You're Ready!

**Congratulations!** You now have:
- ✅ Working OMR Scanner app
- ✅ Understanding of main features
- ✅ Ability to customize
- ✅ Knowledge of project structure

**Next Steps**:
1. Explore the codebase
2. Read advanced documentation
3. Customize for your needs
4. Integrate with backend (see INTEGRATION_GUIDE.md)
5. Deploy to production

---

## 📝 Quick Commands Reference

```bash
# Development
npm run dev          # Start dev server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run linter

# Testing
npm run type-check   # Check TypeScript types

# Deployment
vercel deploy        # Deploy to Vercel
```

---

## 🌟 What's New in v1.1

- 📊 Statistics Dashboard
- 🔍 Search & Filtering
- 📥 Export (CSV/PDF)
- ⚙️ Settings Panel
- 📈 Interactive Charts
- ⚡ Quick Actions
- 🎨 Enhanced Animations

See [WHATS_NEW.md](./WHATS_NEW.md) for details.

---

**Version**: 1.1.0  
**Last Updated**: July 8, 2026  
**Difficulty**: Easy  
**Time to Complete**: 5 minutes

**Happy Coding!** 🚀
