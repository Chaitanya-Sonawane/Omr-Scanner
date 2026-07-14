#!/bin/bash
# Startup script for OMR Scanner System

echo "🚀 Starting OMR Scanner System..."
echo ""

# Check if Python virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install -q -r requirements.txt
pip install -q -r requirements.api.txt

# Start API server in background
echo "🌐 Starting API Server on port 8000..."
python3 api_server.py &
API_PID=$!
echo "   API Server PID: $API_PID"

# Wait for API to start
sleep 3

# Start frontend (Vite/React in omr-web/frontend)
echo "🎨 Starting Frontend on port 3000..."
cd omr-web/frontend
npm install --silent
npm run dev &
FRONTEND_PID=$!
cd ../..

echo ""
echo "✅ OMR Scanner System is running!"
echo ""
echo "📍 Access Points:"
echo "   🖥️  Frontend UI:  http://localhost:3000"
echo "   🔌 API Server:   http://localhost:8000"
echo "   📚 API Docs:     http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services..."
echo ""

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping services...'; kill $API_PID $FRONTEND_PID; exit" INT
wait
