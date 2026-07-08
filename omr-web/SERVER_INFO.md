# OMR Web Application - Server Running ✅

## 🌐 Access URLs

### Primary (Localhost):
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000

### Network Access (from other devices on same network):
- **Frontend:** http://10.236.195.246:3000
- **Backend API:** http://10.236.195.246:8000

---

## ✅ Server Status

Both servers are **RUNNING** and ready to use!

- ✅ Backend (FastAPI) - Port 8000
- ✅ Frontend (React + Vite) - Port 3000
- ✅ API Proxy configured correctly
- ✅ CORS enabled

---

## 📱 How to Access

### On This Computer:
1. Open your web browser (Chrome, Firefox, Edge, etc.)
2. Go to: **http://localhost:3000**
3. You should see the OMR Evaluator interface

### From Another Device (Phone/Tablet/Another Computer):
1. Make sure you're on the same WiFi/Network
2. Open browser and go to: **http://10.236.195.246:3000**

---

## 🔧 Troubleshooting

If the page doesn't load:

1. **Check if servers are still running:**
   ```bash
   ps aux | grep -E "(uvicorn|vite)" | grep -v grep
   ```

2. **Check the logs:**
   ```bash
   # Backend log
   tail -f omr-web/backend/backend.log
   
   # Frontend log  
   tail -f omr-web/frontend/frontend.log
   ```

3. **Test API directly:**
   ```bash
   curl http://localhost:8000/api/session -X POST
   ```
   Should return: `{"session_id":"..."}`

4. **Restart servers if needed:**
   ```bash
   # Kill existing processes
   pkill -f uvicorn
   pkill -f vite
   
   # Restart backend
   cd omr-web/backend
   nohup uvicorn main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
   
   # Restart frontend
   cd omr-web/frontend
   nohup npm run dev > frontend.log 2>&1 &
   ```

---

## 🎯 Quick Test

Run this to verify everything is working:
```bash
# Test backend
curl http://localhost:8000/api/session -X POST

# Test frontend
curl -s http://localhost:3000 | grep "OMR"
```

---

## 📝 Usage Instructions

1. **Upload Answer Key** - First, upload the OMR sheet with correct answers
2. **Upload Student Sheets** - Upload up to 50 student OMR sheets (photos)
3. **Process** - Click process and watch real-time progress
4. **Download Report** - Get PDF with all results

---

**Created:** $(date)
**Backend URL:** http://localhost:8000
**Frontend URL:** http://localhost:3000
