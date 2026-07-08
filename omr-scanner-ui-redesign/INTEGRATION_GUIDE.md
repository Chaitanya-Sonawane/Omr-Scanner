# OMR Scanner - UI/UX Integration Guide

## Overview

This is a professional, responsive OMR (Optical Mark Recognition) Scanner web application built with Next.js 16, React 19, and Tailwind CSS. It provides a complete 4-step workflow for processing exam answer sheets.

## Technology Stack

- **Frontend Framework**: Next.js 16 with App Router
- **UI Component Framework**: React 19 with functional components & hooks
- **Styling**: Tailwind CSS v4 with semantic design tokens
- **Icons**: Lucide React
- **State Management**: React hooks with custom `useOMRState` hook
- **Build Tool**: Turbopack (Next.js 16 default)

## Project Structure

```
app/
├── layout.tsx                 # Root layout with metadata
├── page.tsx                   # Main app page with 4-step workflow
└── globals.css                # Design tokens & Tailwind config

components/omr/
├── Header.tsx                 # Top navigation with session info
├── StepIndicator.tsx          # Visual progress indicator
├── DragDropZone.tsx           # Reusable file upload component
├── StatusBadge.tsx            # Status display with icons
├── SkeletonLoader.tsx         # Loading state UI
├── Toast.tsx                  # Toast notifications (ready to use)
└── steps/
    ├── AnswerKeySetup.tsx     # Step 1: Answer key configuration
    ├── SheetUploadStep.tsx     # Step 2: Student sheet upload
    ├── ProcessingStep.tsx      # Step 3: Real-time processing queue
    └── ResultsStep.tsx         # Step 4: Results & analytics

hooks/
└── useOMRState.ts             # Custom hook for app state management
```

## Design System

### Color Scheme
- **Primary**: Blue/Indigo (0.45 lightness, 0.25 chroma, 270 hue)
- **Accent/Success**: Green (0.65 lightness, 0.2 chroma, 120 hue)
- **Warning**: Yellow/Orange (0.7 lightness, 0.2 chroma, 70 hue)
- **Destructive/Error**: Red (0.58 lightness, 0.25 chroma, 25 hue)
- **Neutrals**: Grays at various lightness levels

### Typography
- **Headings**: Uses system fonts (Geist)
- **Body**: Uses system fonts (Geist)
- **Monospace**: Uses system monospace (Geist Mono)

### Spacing & Border Radius
- **Base radius**: 0.75rem (12px)
- **Spacing scale**: Tailwind standard (4px base unit)

## Features

### ✅ Implemented

1. **Step 1: Answer Key Setup**
   - Upload OMR sheet image (simulates OCR extraction)
   - Manual entry with 40-question grid (4 columns)
   - Use saved answer key (placeholder for stored keys)
   - Visual confirmation when key is set

2. **Step 2: Sheet Upload**
   - Drag & drop multi-file upload
   - Optional student name/ID entry for each sheet
   - File list preview with size information
   - Enabled only after answer key is set

3. **Step 3: Live Processing**
   - Real-time processing queue visualization
   - Individual progress bars per sheet
   - Status badges (Queued, Processing, Done, Error)
   - Summary statistics (total, completed, errors)
   - Grid view for compact display

4. **Step 4: Results Display**
   - Summary cards (Total sheets, Average score, Pass rate)
   - Sortable results table with sticky header
   - Per-student score breakdown (Intelligence, Science, Social, Math)
   - Expandable rows showing answer-by-answer breakdown
   - Color-coded answers (green=correct, red=wrong)
   - Export buttons (PDF, Excel)

5. **UI/UX Features**
   - Responsive design (mobile, tablet, desktop)
   - Step progress indicator with visual state
   - Accessibility (ARIA labels, semantic HTML, keyboard navigation)
   - Smooth animations & transitions
   - Skeleton loaders for async states
   - Professional color scheme & typography
   - Touch-friendly interface on mobile

## Integration with Backend

### API Endpoints to Connect

The UI is designed to work with these FastAPI backend endpoints:

```typescript
// Session Management
POST /api/session                          // Create new session
GET /api/session/{id}/status              // Get session status

// Answer Key
POST /api/session/{id}/answer-key         // Upload answer key image
POST /api/session/{id}/answer-key/manual  // Set answer key manually
GET /api/session/{id}/answer-key          // Retrieve saved answer key

// Student Sheets
POST /api/session/{id}/sheets             // Upload student answer sheets
GET /api/session/{id}/progress            // SSE stream for real-time updates

// Results
GET /api/session/{id}/results             // Get detailed results
GET /api/session/{id}/report              // Download PDF report
GET /api/summary-report                   // Download summary PDF
GET /api/export/excel                     // Download Excel export
```

### Integration Steps

1. **Replace Mock Data with API Calls**
   
   Update `components/omr/steps/AnswerKeySetup.tsx`:
   ```typescript
   const handleConfirm = async () => {
     const response = await fetch(`/api/session/${sessionId}/answer-key/manual`, {
       method: 'POST',
       body: JSON.stringify(manualAnswers),
     });
     onKeySet(manualAnswers);
   };
   ```

2. **Connect File Upload**
   
   Update `components/omr/steps/SheetUploadStep.tsx`:
   ```typescript
   const handleUpload = async () => {
     const formData = new FormData();
     selectedSheets.forEach(file => formData.append('files', file));
     
     const response = await fetch(`/api/session/${sessionId}/sheets`, {
       method: 'POST',
       body: formData,
     });
     onSheetsSelected(selectedSheets, studentNames);
   };
   ```

3. **Connect SSE Processing Stream**
   
   Update `components/omr/steps/ProcessingStep.tsx`:
   ```typescript
   useEffect(() => {
     const eventSource = new EventSource(
       `/api/session/${sessionId}/progress`
     );
     
     eventSource.onmessage = (event) => {
       const data = JSON.parse(event.data);
       setDisplayItems(prev => 
         prev.map(item => 
           item.id === data.sheet_id 
             ? { ...item, status: data.status, progress: data.progress }
             : item
         )
       );
     };
     
     return () => eventSource.close();
   }, [sessionId]);
   ```

4. **Fetch Results Data**
   
   Update `app/page.tsx`:
   ```typescript
   useEffect(() => {
     if (completedSteps.includes(3)) {
       fetch(`/api/session/${sessionId}/results`)
         .then(r => r.json())
         .then(setResults);
     }
   }, [completedSteps]);
   ```

## Responsive Design

### Breakpoints
- **Mobile**: < 768px (320px, 375px, 425px tested)
- **Tablet**: 768px - 1024px  
- **Desktop**: > 1024px

### Mobile Optimizations
- Stack sections vertically
- Single-column results table
- Touch-friendly button sizes (min 44x44px)
- Collapsible sections
- Simplified modals

## Customization

### Adding Custom Styling

Edit `/app/globals.css` to modify design tokens:
```css
:root {
  --primary: oklch(0.45 0.25 270);  /* Change primary color */
  --accent: oklch(0.65 0.2 120);    /* Change success color */
  --border-radius: 0.75rem;         /* Change border radius */
}
```

### Adding Toast Notifications

The `Toast` component is ready to use:
```typescript
import { useContext } from 'react';
import { ToastContext } from '@/components/omr/Toast';

function MyComponent() {
  const { addToast } = useContext(ToastContext);
  
  const handleSubmit = async () => {
    try {
      // ...your logic
      addToast('Success!', 'success');
    } catch (error) {
      addToast('Error occurred', 'error');
    }
  };
}
```

### Modifying the Workflow

To add or remove steps:
1. Update the `steps` array in `app/page.tsx`
2. Create/remove component files in `components/omr/steps/`
3. Update the state management in `hooks/useOMRState.ts`

## Performance Considerations

- **Code Splitting**: Each step component is separately bundled
- **Image Optimization**: Use Next.js `<Image>` for OMR previews
- **Lazy Loading**: Modals and expandable sections load on demand
- **SSE Streaming**: Real-time processing updates without polling
- **Skeleton Loaders**: Reduce perceived load time

## Accessibility Features

- ✅ Semantic HTML (`<main>`, `<nav>`, `<header>`, `<footer>`)
- ✅ ARIA labels for interactive elements
- ✅ Keyboard navigation throughout
- ✅ Color not the only indicator (icons, text labels)
- ✅ Form labels properly associated
- ✅ Focus management in modals
- ✅ Screen reader announcements via `aria-live`

## Browser Support

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Mobile browsers: iOS Safari 14+, Chrome Android 90+

## Deployment

### Vercel (Recommended)
```bash
npm run build
vercel deploy
```

### Self-Hosted
```bash
npm run build
npm run start
```

## Environment Variables

```
NEXT_PUBLIC_API_URL=http://localhost:8000  # FastAPI backend URL
```

## Development

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev

# Open http://localhost:3000

# Build for production
pnpm build

# Run production build
pnpm start
```

## Troubleshooting

### Q: Upload zone not accepting files?
A: Check CORS headers on backend. Files must be images (MIME type validation).

### Q: Processing queue not updating?
A: Verify SSE endpoint is returning proper format: `{"status":"done","score":30,...}`

### Q: Mobile layout breaking?
A: Check viewport meta tag in `layout.tsx`. Use responsive classes: `md:` and `lg:` prefixes.

### Q: Colors not applying?
A: Clear Tailwind cache: `rm -rf .next && pnpm dev`

## License

Created with v0.dev - Educational use

## Support

For UI/UX issues, refer to this documentation. For backend integration issues, check your FastAPI server logs.
