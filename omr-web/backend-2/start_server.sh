#!/bin/bash
exec ../../.venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8001 --reload
