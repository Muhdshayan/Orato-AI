from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends
from app.models.video import VideoUploadRequest, VideoUploadResponse, VideoStatusResponse
from app.services.video_service import VideoService
# [NEW] Import for CV metrics
from app.services.visual_analysis_service import visual_analysis_service
from app.core.database import execute_query
from app.core.config import settings
from app.api.users import get_current_user
import tempfile
import os

# Create router instance
router = APIRouter()

# Initialize video service
video_service = VideoService()

@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Video file to upload"),
    topic: str = Form(..., description="Presentation topic"),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload video for processing (requires authentication)
    
    - **file**: Video file (MP4, AVI, MOV, MKV)
    - **topic**: What the presentation is about
    
    Returns submission ID and processing status
    """
    
    # Validate file type
    allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv']
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Validate file size (100MB limit)
    max_size = 100 * 1024 * 1024  # 100MB
    if file.size and file.size > max_size:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size: 100MB"
        )
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Generate submission ID immediately
        import uuid
        submission_id = str(uuid.uuid4())
        
        # Create initial database entry with "processing" status
        # Use placeholder values for MinIO fields that will be updated during processing
        from app.core.database import execute_query
        placeholder_minio_object = f"uploads/{submission_id}.mp4"  # Will be updated with actual path
        execute_query(
            """
            INSERT INTO video_submissions (submission_id, user_id, filename, filesize, declared_topic, 
                                          minio_bucket, minio_object_name, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (submission_id, current_user["user_id"], file.filename, file.size or 0, topic,
             settings.MINIO_MEDIA_BUCKET, placeholder_minio_object, "processing")
        )
        print(f"✅ Created submission {submission_id} with status 'processing'")
        
        # Process video in background (don't wait for it to complete)
        background_tasks.add_task(
            video_service.process_video_background,
            temp_file_path,
            submission_id,
            topic,
            current_user["user_id"]
        )
        print(f"🚀 Background processing started for submission {submission_id}")
        
        # Return immediately with submission_id and processing status
        response_data = {
            "submission_id": submission_id,
            "status": "processing",
            "message": "Video uploaded successfully. Processing in background.",
            "files": None
        }
        return VideoUploadResponse(**response_data)
        
    except Exception as e:
        # Cleanup temp file if it exists
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                print(f"🧹 Cleaned up temp file after error: {temp_file_path}")
            except:
                pass
        
        print(f"❌ Upload endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Video processing failed: {str(e)}"
        )

@router.get("/{submission_id}/status", response_model=VideoStatusResponse)
async def get_video_status(submission_id: str):
    """
    Get video processing status
    
    - **submission_id**: Unique submission identifier
    
    Returns current processing status and progress
    """
    try:
        status = await video_service.get_status(submission_id)
        
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        
        return VideoStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )

@router.get("/{submission_id}/files")
async def get_video_files(submission_id: str):
    """
    Get video file URLs
    
    - **submission_id**: Unique submission identifier
    
    Returns presigned URLs for all video files
    """
    try:
        # Get submission details from database
        query = """
        SELECT submission_id, filename, filesize, declared_topic, minio_object_name
        FROM video_submissions 
        WHERE submission_id = %s
        """
        result = execute_query(query, (submission_id,), fetch_one=True)
        
        if not result:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        # Generate file URLs
        files = {
            "original": video_service.minio.get_presigned_url(result["minio_object_name"]),
            "video_only": video_service.minio.get_presigned_url(f"derived/{submission_id}_video_only.mp4"),
            "audio_only": video_service.minio.get_presigned_url(f"derived/{submission_id}_audio_only.wav")
        }
        
        return {
            "submission_id": submission_id,
            "files": files,
            "original_filename": result["filename"],
            "file_size": result["filesize"],
            "topic": result["declared_topic"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get files: {str(e)}"
        )

# [NEW] Endpoint to retrieve CV Analysis Results
@router.get("/{submission_id}/cv-metrics")
async def get_cv_metrics(submission_id: str):
    """
    Fetch the Visual Analysis (Body Language) results.
    """
    try:
        # Fetch from the service helper
        result = visual_analysis_service.get_analysis_result(submission_id)
        
        if not result:
            # Check if job exists to determine if it's processing or just missing
            status_check = await video_service.get_status(submission_id)
            if status_check.get("status") in ["uploaded", "processing"]:
                 return {"status": "processing", "message": "Visual analysis is still running"}
            return {"status": "not_found", "message": "No visual analysis found for this video"}
            
        return result
        
    except Exception as e:
        print(f"❌ API Error fetching CV metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch CV metrics: {str(e)}")