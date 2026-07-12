# Deployment Guide - OMR Scanner

This guide covers deploying the OMR Scanner application with the integrated template-based scanner and mobile capture frontend.

## Architecture

- **Backend (Render)**: FastAPI server with template-based OMR scanner
- **Frontend (Netlify)**: React web application with mobile capture interface
- **Mobile Capture**: Camera-based scanning with real-time quality checks

## Prerequisites

- GitHub account with the repository cloned
- Render account (free tier available)
- Netlify account (free tier available)

## Step 1: Deploy Backend to Render

### 1.1 Create Render Service

1. Go to [render.com](https://render.com) and sign up/login
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Select branch: `upgrade/scanner-preprocessor`
5. Configure:
   - **Name**: `omr-scanner-backend`
   - **Root Directory**: `omr-web/backend-2`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api_server:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free (or paid for better performance)

### 1.2 Environment Variables

Add these environment variables in Render:

```
PORT=8001
PYTHON_VERSION=3.10.0
```

### 1.3 Deploy

Click "Create Web Service". Render will:
- Clone your repository
- Install dependencies
- Start the FastAPI server
- Provide a URL like: `https://omr-scanner-backend.onrender.com`

**Note**: Copy this URL for the next steps.

## Step 2: Deploy Frontend to Netlify

### 2.1 Build Frontend Locally First

```bash
cd omr-web/frontend
npm install
npm run build
```

### 2.2 Connect to Netlify

1. Go to [netlify.com](https://netlify.com) and sign up/login
2. Click "Add new site" → "Import an existing project"
3. Connect your GitHub repository
4. Configure build settings:
   - **Build command**: `npm run build`
   - **Publish directory**: `dist`
   - **Base directory**: `omr-web/frontend`

### 2.3 Add Environment Variables

In Netlify site settings → Environment variables:

```
VITE_API_URL=https://omr-scanner-backend.onrender.com
```

Replace with your actual Render backend URL.

### 2.4 Deploy

Click "Deploy site". Netlify will:
- Clone your repository
- Install dependencies
- Build the React app
- Deploy to CDN
- Provide a URL like: `https://omr-scanner.netlify.app`

## Step 3: Configure Mobile Capture

The mobile capture interface is served from the backend at `/mobile`. To make it accessible:

### Option A: Serve from Backend (Recommended)

The mobile capture is already mounted in backend-2 at `/mobile`. Access it at:
```
https://omr-scanner-backend.onrender.com/mobile
```

### Option B: Serve from Netlify

If you want mobile capture on the same domain as the frontend:

1. Copy the mobile directory to the frontend public folder:
```bash
cp -r omr-web/frontend/mobile omr-web/frontend/public/mobile
```

2. Update netlify.toml to remove the mobile redirect:
```toml
[[redirects]]
  from = "/api/*"
  to = "https://omr-scanner-backend.onrender.com/api/:splat"
  status = 200
  force = true
```

## Step 4: Test Deployment

### 4.1 Test Backend Health

```bash
curl https://omr-scanner-backend.onrender.com/health
```

Expected response:
```json
{"status":"ok","template_loaded":true}
```

### 4.2 Test Mobile API

```bash
curl https://omr-scanner-backend.onrender.com/api/mobile/health
```

Expected response:
```json
{"status":"ok","template_available":true,"questions":40}
```

### 4.3 Test Frontend

Open your Netlify URL and verify:
- Desktop interface loads
- Mobile Scan button works
- Can create sessions
- Can upload answer keys

### 4.4 Test Mobile Capture

Open the mobile capture URL on a mobile device:
```
https://omr-scanner-backend.onrender.com/mobile
```

Verify:
- Camera permission request
- Live preview with guidance
- Quality checks work
- Image upload and processing

## Step 5: Calibrate Template (First Time Only)

Before scanning, you need to calibrate the template:

1. Have a clean, blank OMR sheet
2. Use the calibration endpoint:
```bash
curl -X POST https://omr-scanner-backend.onrender.com/api/calibrate \
  -F "file=@clean_reference_sheet.jpg"
```

This generates/updates `template.json` with bubble coordinates.

## Troubleshooting

### Backend fails to start

- Check Render logs for dependency errors
- Ensure `requirements.txt` is in the root directory
- Verify Python version compatibility

### Frontend API calls fail

- Verify `VITE_API_URL` is set correctly in Netlify
- Check CORS settings in backend
- Ensure backend is running and accessible

### Mobile capture not working

- Verify camera permissions on mobile device
- Check that mobile API endpoints are accessible
- Ensure HTTPS is enabled (required for camera access)

### Template not loaded

- Run calibration with a clean reference sheet
- Check that `template.json` exists in backend-2
- Verify template has 160 bubbles (40 questions × 4 options)

## Performance Optimization

### Backend (Render)

- Upgrade to paid instance for faster processing
- Add Redis for session caching
- Use CDN for static assets

### Frontend (Netlify)

- Enable Netlify Edge Functions for API proxying
- Use image optimization
- Enable caching headers

### Mobile Capture

- Reduce image quality for faster uploads
- Implement client-side image compression
- Use progressive image loading

## Security Considerations

1. **API Authentication**: Add API keys or OAuth for production
2. **Rate Limiting**: Implement rate limiting on backend
3. **Input Validation**: Validate all uploaded files
4. **HTTPS**: Always use HTTPS in production
5. **CORS**: Restrict CORS to allowed origins only

## Monitoring

### Render Monitoring

- Render provides built-in metrics
- Check CPU, memory, and response times
- Set up alerts for failures

### Netlify Monitoring

- Netlify provides deployment logs
- Check build failures
- Monitor edge function performance

## Cost Estimates

### Render (Free Tier)
- 512 MB RAM
- 0.1 CPU
- 750 hours/month
- Suitable for development/testing

### Netlify (Free Tier)
- 100GB bandwidth/month
- 300 build minutes/month
- Unlimited sites
- Suitable for production

### Paid Tier Recommendations
- **Render**: $7/month for better performance
- **Netlify**: $19/month for advanced features

## Support

For issues:
1. Check Render logs
2. Check Netlify deploy logs
3. Review this guide
4. Open an issue on GitHub
