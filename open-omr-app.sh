#!/bin/bash

echo "=========================================="
echo "  OMR Web Application Status"
echo "=========================================="
echo ""

# Check if servers are running
if ps aux | grep -v grep | grep -q "uvicorn.*8000"; then
    echo "✅ Backend Server: RUNNING on port 8000"
else
    echo "❌ Backend Server: NOT RUNNING"
    echo "   Starting backend..."
    cd omr-web/backend
    nohup uvicorn main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
    cd ../..
    sleep 2
fi

if ps aux | grep -v grep | grep -q "vite"; then
    echo "✅ Frontend Server: RUNNING on port 3000"
else
    echo "❌ Frontend Server: NOT RUNNING"
    echo "   Starting frontend..."
    cd omr-web/frontend
    nohup npm run dev > frontend.log 2>&1 &
    cd ../..
    sleep 3
fi

echo ""
echo "=========================================="
echo "  Access URLs"
echo "=========================================="
echo ""
echo "🌐 Open in your browser:"
echo "   http://localhost:3000"
echo ""
echo "📱 Or from another device:"
echo "   http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo "=========================================="
echo ""

# Try to open in default browser
if command -v xdg-open > /dev/null; then
    echo "Opening in browser..."
    xdg-open http://localhost:3000 2>/dev/null &
elif command -v gnome-open > /dev/null; then
    gnome-open http://localhost:3000 2>/dev/null &
elif command -v firefox > /dev/null; then
    firefox http://localhost:3000 2>/dev/null &
elif command -v google-chrome > /dev/null; then
    google-chrome http://localhost:3000 2>/dev/null &
else
    echo "⚠️  Could not automatically open browser."
    echo "   Please manually open: http://localhost:3000"
fi

echo ""
echo "Press Ctrl+C to stop watching logs..."
echo ""
sleep 2
tail -f omr-web/frontend/frontend.log
