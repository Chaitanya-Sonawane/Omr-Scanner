#!/usr/bin/env python3
"""
Server startup script for OMR backend
"""
import uvicorn
import sys
import os

if __name__ == "__main__":
    print("🚀 Starting OMR Backend Server...")
    print("📍 Backend API: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("🌐 Frontend: http://localhost:3000")
    print("-" * 50)
    
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            access_log=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)