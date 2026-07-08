# 🏗️ Component Hierarchy - OMR Scanner

## Visual Structure

```
┌─────────────────────────────────────────────────────────────┐
│                         App (page.tsx)                       │
│                    ┌──────────────────────┐                 │
│                    │   useOMRState Hook   │                 │
│                    └──────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
┌───────▼───────┐                         ┌─────────▼─────────┐
│  Header.tsx   │                         │  Main Content     │
├───────────────┤                         └───────────────────┘
│ ┌───────────┐ │                                 │
│ │ Settings  │ │                    ┌────────────┼────────────┐
│ │  Button   │ │                    │            │            │
│ └─────┬─────┘ │         ┌──────────▼─┐   ┌─────▼─────┐   ┌─▼──────┐
│       │       │         │  Step      │   │  Step     │   │ Footer │
│   ┌───▼──────┐│         │ Indicator  │   │ Content   │   └────────┘
│   │Settings  ││         └────────────┘   └───────────┘
│   │  Panel   ││                               │
│   └──────────┘│                    ┌──────────┼──────────┐
└───────────────┘                    │          │          │
                              ┌──────▼───┐ ┌───▼──────┐ ┌─▼────────┐
                              │ Answer   │ │  Sheet   │ │Processing│
                              │   Key    │ │  Upload  │ │   Step   │
                              │  Setup   │ │   Step   │ └──────────┘
                              └──────────┘ └──────────┘      │
                                                         ┌────▼────┐
                                                         │ Results │
                                                         │  Step   │
                                                         └─────────┘
```

---

## Detailed Component Breakdown

### 1. App Level (page.tsx)
```
page.tsx (Main App)
│
├── useOMRState() Hook
│   ├── Session management
│   ├── State management
│   └── Processing simulation
│
├── Header
├── StepIndicator
├── AnswerKeySetup (Step 1)
├── SheetUploadStep (Step 2)
├── ProcessingStep (Step 3)
└── ResultsStep (Step 4)
```

---

### 2. Header Component
```
Header.tsx
│
├── Logo Section
│   ├── Icon
│   └── Title + Subtitle
│
├── Session ID Display
│
└── Settings Button
    └── Opens → SettingsPanel
```

**Children**:
- `SettingsPanel.tsx` (Modal overlay)

---

### 3. Settings Panel Component
```
SettingsPanel.tsx
│
├── Backdrop (Click to close)
│
└── Panel (Slides from right)
    │
    ├── Header
    │   ├── Title
    │   └── Close Button
    │
    ├── Grading Settings
    │   └── Passing Score Input
    │
    ├── Appearance Settings
    │   └── Dark Mode Toggle
    │
    ├── Export Settings
    │   └── Auto Export Toggle
    │
    ├── Notifications Settings
    │   └── Show Notifications Toggle
    │
    └── Save Button
```

**Dependencies**: None  
**State**: Local (5 state variables)  
**Persistence**: localStorage

---

### 4. Step Indicator
```
StepIndicator.tsx
│
└── Steps Array (Horizontal on desktop, Vertical on mobile)
    │
    ├── Step 1: Answer Key
    ├── Step 2: Upload Sheets
    ├── Step 3: Processing
    └── Step 4: Results
```

**Props**:
- `steps`: Array of step objects

---

### 5. Answer Key Setup (Step 1)
```
AnswerKeySetup.tsx
│
├── Tab Selection
│   ├── Upload Image
│   ├── Manual Entry ✓ (Active in demo)
│   └── Use Saved
│
└── Manual Entry Tab
    │
    ├── Grid (40 questions, 4 columns)
    │   └── Radio buttons (A, B, C, D)
    │
    └── Confirm Button
```

**Children**: None  
**Props**: `onKeySet`, `isKeySet`

---

### 6. Sheet Upload Step (Step 2)
```
SheetUploadStep.tsx
│
└── DragDropZone
    │
    ├── Drag & Drop Area
    │   ├── Upload Icon (Animated)
    │   ├── Label
    │   └── Description
    │
    └── File List (If files selected)
        │
        └── File Items (Staggered animation)
            ├── Filename
            ├── File size
            └── Remove button
```

**Children**:
- `DragDropZone.tsx` (Reusable)

---

### 7. Drag Drop Zone Component
```
DragDropZone.tsx (Reusable)
│
├── Drop Zone
│   ├── Hover state (Scale 1.01x)
│   ├── Drag active (Scale 1.02x + pulse)
│   └── File input (Hidden)
│
└── File List (Optional)
    │
    └── File Item (Per file, animated)
        ├── Name
        ├── Size
        └── Remove button (Scale on hover)
```

**Props**: `onFilesSelected`, `accept`, `multiple`, `disabled`, etc.  
**State**: `isDragging`

---

### 8. Processing Step (Step 3)
```
ProcessingStep.tsx
│
├── Summary Stats
│   ├── Total sheets
│   ├── Completed count
│   └── Progress percentage
│
└── Processing Queue (Grid)
    │
    └── Processing Items (3-4 per row)
        │
        └── Card per sheet
            ├── Filename
            ├── Student ID
            ├── Status Badge
            └── Progress Bar
```

**Children**:
- `StatusBadge.tsx`

**Props**: `items`, `isProcessing`, `isVisible`

---

### 9. Results Step (Step 4) ⭐ Enhanced
```
ResultsStep.tsx ⭐ ENHANCED
│
├── Header
│   ├── Title
│   └── Show/Hide Analytics Button
│
├── Charts Section (Toggle-able) ✨ NEW
│   └── ChartVisualization
│
├── Statistics Dashboard ✨ NEW
│   └── StatisticsDashboard
│       ├── Total Students Card
│       ├── Average Score Card
│       ├── Pass Rate Card
│       ├── Highest Score Card
│       ├── Lowest Score Card
│       └── At Risk Card
│
├── Quick Actions ✨ NEW
│   └── QuickActions
│       ├── Export CSV Button
│       ├── Print Button
│       ├── Share Button
│       └── Refresh Button
│
├── Search & Filters ✨ ENHANCED
│   ├── Search Bar (Real-time) ✨ NEW
│   ├── Sort Dropdown (Score/Name)
│   ├── Filter Dropdown (All/Pass/Fail) ✨ NEW
│   └── Result Count ✨ NEW
│
├── Results Table (Desktop)
│   │
│   ├── Header Row (Sticky)
│   │
│   └── Data Rows (Expandable)
│       │
│       ├── Student Info
│       ├── Scores
│       ├── Expand Button
│       │
│       └── Expanded Section
│           └── Answer Details Grid
│               └── Question Cards (Color-coded)
│
└── Results Cards (Mobile)
    │
    └── Card per student
        ├── Header (Name + Score)
        ├── Score Grid (4 subjects)
        ├── Expand Button
        └── Answer Details (Expandable)
```

**New Children**:
- `StatisticsDashboard.tsx` ✨
- `QuickActions.tsx` ✨
- `ChartVisualization.tsx` (Integrated)

**Enhanced Features**:
- Search functionality ✨
- Multi-criteria filtering ✨
- Export CSV ✨
- Print/PDF ✨
- useMemo for performance ✨

---

## Component Dependency Graph

```
page.tsx
  ├── Header
  │     └── SettingsPanel ✨ NEW
  │
  ├── StepIndicator
  │
  ├── AnswerKeySetup
  │
  ├── SheetUploadStep
  │     └── DragDropZone (Enhanced)
  │
  ├── ProcessingStep
  │     └── StatusBadge
  │
  └── ResultsStep (Enhanced)
        ├── StatisticsDashboard ✨ NEW
        ├── QuickActions ✨ NEW
        └── ChartVisualization
```

---

## Reusable Components

### UI Components (Can be used anywhere)

1. **DragDropZone.tsx**
   - File upload with drag & drop
   - Animations and feedback
   - File list management

2. **StatusBadge.tsx**
   - Status indicator
   - Icon + text
   - Color-coded

3. **SkeletonLoader.tsx**
   - Loading placeholder
   - Animated shimmer

4. **Toast.tsx**
   - Notification system
   - Context provider
   - Auto-dismiss

5. **ErrorBoundary.tsx**
   - Error catching
   - Fallback UI

6. **SettingsPanel.tsx** ✨ NEW
   - Modal overlay
   - Settings management
   - Slide-in animation

7. **StatisticsDashboard.tsx** ✨ NEW
   - Metric cards
   - Hover effects
   - Responsive grid

8. **QuickActions.tsx** ✨ NEW
   - Action buttons
   - Icon-based UI
   - Mobile-optimized

9. **ProgressTracker.tsx** ✨ NEW
   - Step visualization
   - Animations
   - Horizontal/Vertical layouts

10. **ChartVisualization.tsx**
    - Bar charts
    - Score distribution
    - Statistics

---

## Data Flow

### State Management (useOMRState Hook)

```
useOMRState()
  │
  ├── State
  │   ├── sessionId
  │   ├── answerKey
  │   ├── selectedSheets
  │   ├── processingItems
  │   ├── results
  │   ├── isProcessing
  │   ├── currentStep
  │   └── completedSteps
  │
  ├── Actions
  │   ├── handleAnswerKeySet()
  │   ├── handleSheetsSelected()
  │   └── resetSession()
  │
  └── Effects
      └── Session ID generation on mount
```

### Props Flow

```
App (page.tsx)
  │
  ├─→ Header
  │     props: { sessionId }
  │
  ├─→ StepIndicator
  │     props: { steps }
  │
  ├─→ AnswerKeySetup
  │     props: { onKeySet, isKeySet }
  │
  ├─→ SheetUploadStep
  │     props: { onSheetsSelected, isKeySet }
  │
  ├─→ ProcessingStep
  │     props: { items, isProcessing, isVisible }
  │
  └─→ ResultsStep
        props: { results, isVisible }
```

---

## Event Flow

### User Interaction Flow

```
1. User clicks "Settings"
   → Header.onClick()
   → setIsSettingsOpen(true)
   → SettingsPanel renders

2. User changes setting
   → SettingsPanel.onChange()
   → Update local state
   → Click "Save" → localStorage.setItem()

3. User enters answer key
   → AnswerKeySetup.onConfirm()
   → handleAnswerKeySet()
   → setAnswerKey()
   → setCurrentStep(2)

4. User uploads sheets
   → DragDropZone.onDrop()
   → SheetUploadStep.onSheetsSelected()
   → handleSheetsSelected()
   → simulateProcessing()
   → setCurrentStep(3)

5. Processing completes
   → handleProcessingComplete()
   → setResults()
   → setCurrentStep(4)

6. User searches results
   → ResultsStep.onChange() ✨ NEW
   → setSearchQuery()
   → useMemo filters results
   → Re-render filtered list

7. User exports CSV
   → QuickActions.onClick() ✨ NEW
   → handleExportExcel()
   → Create CSV blob
   → Trigger download
```

---

## File Structure

```
omr-scanner-ui-redesign/
│
├── app/
│   ├── layout.tsx          (Root layout)
│   ├── page.tsx            (Main app)
│   └── globals.css         (Styles + animations)
│
├── components/
│   ├── omr/
│   │   ├── UI Components
│   │   │   ├── Header.tsx ⭐
│   │   │   ├── StepIndicator.tsx
│   │   │   ├── DragDropZone.tsx ⭐
│   │   │   ├── StatusBadge.tsx
│   │   │   ├── SkeletonLoader.tsx
│   │   │   ├── Toast.tsx
│   │   │   ├── ErrorBoundary.tsx
│   │   │   ├── ChartVisualization.tsx
│   │   │   ├── SettingsPanel.tsx ✨
│   │   │   ├── StatisticsDashboard.tsx ✨
│   │   │   ├── QuickActions.tsx ✨
│   │   │   └── ProgressTracker.tsx ✨
│   │   │
│   │   └── steps/
│   │       ├── AnswerKeySetup.tsx
│   │       ├── SheetUploadStep.tsx
│   │       ├── ProcessingStep.tsx
│   │       └── ResultsStep.tsx ⭐
│   │
│   └── ui/
│       └── button.tsx
│
├── hooks/
│   ├── useOMRState.ts      (Main state hook)
│   └── useMediaQuery.ts    (Responsive helper)
│
└── lib/
    └── utils.ts            (Utility functions)

Legend:
⭐ = Enhanced in v1.1
✨ = New in v1.1
```

---

## Component Sizes (Lines of Code)

| Component | Lines | Complexity |
|-----------|-------|------------|
| page.tsx | 85 | Low |
| Header.tsx | 50 | Low |
| SettingsPanel.tsx ✨ | 181 | Medium |
| StepIndicator.tsx | 64 | Low |
| DragDropZone.tsx | 131 | Medium |
| StatusBadge.tsx | 55 | Low |
| SkeletonLoader.tsx | 66 | Low |
| Toast.tsx | 105 | Medium |
| ErrorBoundary.tsx | 40 | Low |
| ChartVisualization.tsx | 150 | Medium |
| StatisticsDashboard.tsx ✨ | 106 | Low |
| QuickActions.tsx ✨ | 51 | Low |
| ProgressTracker.tsx ✨ | 100 | Medium |
| AnswerKeySetup.tsx | 173 | High |
| SheetUploadStep.tsx | 117 | Medium |
| ProcessingStep.tsx | 147 | Medium |
| ResultsStep.tsx | 350+ | High |
| useOMRState.ts | 173 | High |

**Total**: ~2,000+ lines of component code

---

## Component Communication

### Parent-to-Child (Props)
```
App → Header → SettingsPanel
   sessionId    isOpen, onClose

App → ResultsStep → StatisticsDashboard
   results          totalStudents, avgScore, etc.

App → ResultsStep → QuickActions
   results          onExport, onPrint, etc.
```

### Child-to-Parent (Callbacks)
```
AnswerKeySetup → App
   onKeySet(key)

SheetUploadStep → App
   onSheetsSelected(files, info)

SettingsPanel → Header
   onClose()
```

### Sibling Communication (Via Parent State)
```
AnswerKeySetup → App State → SheetUploadStep
   Sets answerKey → Enables upload step

SheetUploadStep → App State → ProcessingStep
   Sets sheets → Starts processing

ProcessingStep → App State → ResultsStep
   Sets results → Shows results
```

---

## Styling Architecture

### Utility-First (Tailwind CSS)
```css
/* Component styles use Tailwind classes */
className="rounded-xl border border-border bg-card p-4"
```

### Custom Animations (globals.css)
```css
@keyframes slide-in-from-right { ... }
@keyframes fade-in { ... }
@keyframes scale-in { ... }
```

### Design Tokens (CSS Variables)
```css
:root {
  --primary: oklch(0.45 0.25 270);
  --accent: oklch(0.65 0.2 120);
  --border: oklch(0.91 0.01 270);
}
```

---

## Best Practices Implemented

### Component Design
✅ Single Responsibility Principle  
✅ Composition over inheritance  
✅ Prop validation with TypeScript  
✅ Controlled components  

### State Management
✅ Custom hooks for logic  
✅ Minimal prop drilling  
✅ Local state where appropriate  
✅ Memoization for performance  

### Styling
✅ Utility-first approach  
✅ Responsive breakpoints  
✅ Dark mode support  
✅ Accessible colors  

### Performance
✅ Code splitting  
✅ Lazy loading  
✅ Memoization  
✅ CSS animations (not JS)  

---

## Quick Reference

### Import Paths
```tsx
// UI Components
import Header from '@/components/omr/Header'
import SettingsPanel from '@/components/omr/SettingsPanel'
import StatisticsDashboard from '@/components/omr/StatisticsDashboard'

// Step Components
import ResultsStep from '@/components/omr/steps/ResultsStep'

// Hooks
import { useOMRState } from '@/hooks/useOMRState'
```

### Common Props
```tsx
// Visibility toggle
interface Props {
  isVisible?: boolean;
}

// Callback pattern
interface Props {
  onAction: (data: Type) => void;
}

// Children pattern
interface Props {
  children: React.ReactNode;
}
```

---

**Last Updated**: July 8, 2026  
**Version**: 1.1.0  
**Complexity**: Medium to High  
**Maintainability**: ✅ Excellent
