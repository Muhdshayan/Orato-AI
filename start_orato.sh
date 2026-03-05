#!/bin/bash

# Ensure we are in the project root
cd "$(dirname "$0")"

echo "========================================="
echo "      Starting Orato-AI Services         "
echo "========================================="

# 1. Start Docker containers
echo "[1/3] Starting Docker containers (PostgreSQL, MinIO)..."
sudo docker start oratoaidb >/dev/null 2>&1 || sudo docker run --name oratoaidb -e POSTGRES_PASSWORD=orato123 -p 5432:5432 -d postgres >/dev/null
sudo docker start minio >/dev/null 2>&1 || sudo docker run -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER=MINIO_ACCESS -e MINIO_ROOT_PASSWORD=MINIO_SECRET -v "$(pwd)/minio-data":/data --name minio -d minio/minio server /data --console-address ":9001" >/dev/null

# 2. Start Backend
echo "[2/3] Starting FastAPI Backend (Logs will print below)..."
cd backend
../venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 | tee backend.log &
BACKEND_PID=$!
cd ..
echo $BACKEND_PID > .backend.pid

# 3. Start Frontend
echo "[3/3] Starting React Frontend..."
cd frontend
BROWSER=none npm run start > frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo $FRONTEND_PID > .frontend.pid

echo ""
echo "========================================="
echo "        Orato-AI is now running!         "
echo "========================================="
echo "🌐 Frontend Dashboard : http://localhost:3000"
echo "🔌 Backend API Docs   : http://localhost:8000/docs"
echo "🗄️  MinIO Console      : http://localhost:9001"
echo ""
echo "Logs are being written to backend/backend.log and frontend/frontend.log"
echo "Press Ctrl+C to gracefully stop all services, or run ./stop_orato.sh in another terminal."

# Handle Ctrl+C (SIGINT) gracefully
cleanup() {
    echo ""
    echo "Caught exit signal! Shutting down..."
    ./stop_orato.sh
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait indefinitely until interrupted
wait
