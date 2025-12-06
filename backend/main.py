from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.video import router as video_router
from app.api.users import router as users_router
from app.api.transcript import router as transcript_router
from app.core.config import settings

# Create FastAPI instance with metadata
app = FastAPI(
    title="OratoAI API",
    description="AI-powered presentation analysis and feedback",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI endpoint
    redoc_url="/redoc"  # ReDoc endpoint
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Include video router with prefix and tags
app.include_router(
    video_router,
    prefix="/api/v1/videos",
    tags=["videos"]
)

app.include_router(
    users_router,
    prefix="/api/v1/users",
    tags=["users"]
)

app.include_router(
    transcript_router,
    prefix="/api/v1/transcripts",
    tags=["transcripts"]
)

# Root endpoint - basic health check
@app.get("/")
async def root():
    """Root endpoint returning API information"""
    return {
        "message": "OratoAI API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }

# Health check endpoint for monitoring
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers"""
    return {"status": "healthy", "service": "oratoai-api"}

# Startup event - runs when app starts
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    import os
    import sys
    import subprocess
    import time
    
    # Start Parakeet model server in background
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        venv_path = os.path.join(project_root, 'venv_asr')
        python_exe = os.path.join(venv_path, 'Scripts', 'python.exe')
        server_script = '/workspace/Orato-AI/scripts/parakeet_model_server.py'
        
        if os.path.exists(python_exe) and os.path.exists(server_script):
            print("🚀 Starting Parakeet model server...")
            # Start server in background (Windows: CREATE_NO_WINDOW, detached process)
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                # Use CREATE_NO_WINDOW only (DETACHED_PROCESS can cause issues)
                process = subprocess.Popen(
                    [python_exe, server_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                process = subprocess.Popen(
                    [python_exe, server_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
            
            # Give server a moment to start
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                print("✅ Parakeet model server started successfully")
            else:
                stdout, stderr = process.communicate()
                print(f"⚠️ Model server exited early. Stdout: {stdout.decode()[:200]}, Stderr: {stderr.decode()[:200]}")
                print("   Transcription will fall back to subprocess mode (may be slower)")
        else:
            print("⚠️ Parakeet model server script not found, using fallback subprocess mode")
    except Exception as e:
        print(f"⚠️ Failed to start Parakeet model server: {e}")
        print("   Transcription will fall back to subprocess mode (may be slower)")
        import traceback
        traceback.print_exc()
    
    print("🚀 OratoAI API started successfully!")

# Shutdown event - runs when app stops
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🛑 OratoAI API shutting down...")
    
    # Note: Model server process will continue running in background
    # It can be manually stopped or will persist until system restart
    # For production, consider implementing proper process management
