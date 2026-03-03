#!/bin/bash

# Ensure we are in the project root
cd "$(dirname "$0")"

echo "========================================="
echo "      Stopping Orato-AI Services         "
echo "========================================="

# 1. Stop Frontend
echo "[1/3] Stopping React Frontend..."
if [ -f .frontend.pid ]; then
    kill $(cat .frontend.pid) 2>/dev/null
    rm .frontend.pid
fi
# Catch trailing node processes
pkill -f "react-scripts start" 2>/dev/null
pkill -f "npm run start" 2>/dev/null

# 2. Stop Backend & ASR Model Server
echo "[2/3] Stopping FastAPI Backend and ASR Server..."
if [ -f .backend.pid ]; then
    kill $(cat .backend.pid) 2>/dev/null
    rm .backend.pid
fi
# Catch trailing Python processes
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "parakeet_model_server.py" 2>/dev/null

# 3. Stop Docker containers
echo "[3/3] Stopping Docker containers..."
sudo docker stop oratoaidb >/dev/null 2>&1
sudo docker stop minio >/dev/null 2>&1

echo ""
echo "========================================="
echo "    All services stopped successfully!   "
echo "========================================="
