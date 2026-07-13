# Mobile OMR Capture - Netlify Deployment

This directory contains the mobile-only OMR capture interface for deployment on Netlify.

## Architecture

- **Frontend (Netlify)**: Static mobile capture interface
- **Backend (Render)**: FastAPI server with template-based OMR scanner
- **API Proxy**: Netlify redirects `/api/*` to Render backend

## Deployment Steps

### 1. Deploy Backend to Render

First, deploy the backend-2 to Render following the instructions in the main DEPLOYMENT.md.

Copy the Render URL (e.g., `https://omr-scanner-backend.onrender.com`)

### 2. Deploy Mobile Frontend to Netlify

1. Go to [netlify.com](https://netlify.com) and sign up/login
2. Click "Add new site" → "Import an existing project"
3. Connect your GitHub repository
4. Configure build settings:
   - **Base directory**: `mobile-deploy`
   - **Build command**: `echo 'No build needed for static mobile site'`
   - **Publish directory**: `.` (root of mobile-deploy)

### 3. Configure Environment Variables

In Netlify site settings → Environment variables:

```
MOBILE_API_URL=https://omr-scanner-backend.onrender.com
```

Replace with your actual Render backend URL.

### 4. Deploy

Click "Deploy site". Netlify will:
- Clone your repository
- Copy the mobile-deploy directory
- Deploy to CDN
- Provide a URL like: `https://omr-omr-mobile.netlify.app`

## Access Points

- **Mobile Capture**: `https://your-netlify-site.netlify.app`
- **Backend API**: `https://your-render-site.onrender.com/api/*`
- **Mobile API**: Proxied through Netlify to Render

## Configuration Files

- `netlify.toml`: Netlify deployment configuration
- `index.html`: Mobile capture interface with API URL configuration
- `js/app.js`: Mobile app logic with API calls
- `js/capture.js`: Camera capture and upload logic
- `js/quality.js`: Image quality checks
- `js/guidance.js`: Camera guidance overlay
- `css/style.css`: Mobile interface styling

## API Endpoints

The mobile frontend uses these endpoints (proxied via Netlify):

- `POST /api/mobile/session` - Create mobile session
- `POST /api/mobile/scan` - Process mobile camera captures
- `GET /api/mobile/config` - Template configuration
- `GET /api/mobile/health` - Health check

## Testing

### Local Testing

1. Start backend-2 locally:
```bash
cd omr-web/backend-2
uvicorn api_server:app --host 0.0.0.0 --port 8001
```

2. Serve mobile frontend locally:
```bash
cd mobile-deploy
python -m http.server 3000
```

3. Access at: `http://localhost:3000`

### Production Testing

1. Deploy backend to Render
2. Deploy mobile to Netlify
3. Access mobile at your Netlify URL
4. Test camera capture and scanning

## Features

- **Camera Capture**: Auto-capture with quality checks
- **Real-time Guidance**: Aspect ratio, blur, alignment checks
- **Template-based Scanning**: Uses backend-2 template scanner
- **Session Management**: Track multiple sheets in a session
- **Confidence Scoring**: Per-question confidence and retake recommendations

## Troubleshooting

### Camera not working

- Ensure HTTPS is enabled (required for camera access)
- Check browser permissions
- Try on mobile device (desktop browsers may have camera issues)

### API calls failing

- Verify `MOBILE_API_URL` is set correctly in Netlify
- Check that backend is running and accessible
- Verify CORS settings on backend

### Mobile interface not loading

- Check Netlify build logs
- Ensure all files are in the mobile-deploy directory
- Verify netlify.toml configuration

## Cost

- **Netlify**: Free tier sufficient for static mobile site
- **Render**: Free tier for backend (or paid for better performance)

## Support

For issues:
1. Check Netlify deploy logs
2. Check Render logs
3. Review this README
4. Open an issue on GitHub
