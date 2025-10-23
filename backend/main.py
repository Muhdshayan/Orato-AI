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
    print("🚀 OratoAI API started successfully!")

# Shutdown event - runs when app stops
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🛑 OratoAI API shutting down...")
