from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class VideoUploadRequest(BaseModel):
    """Request model for video upload"""
    topic: str = Field(..., description="Presentation topic", min_length=1)
    user_id: str = Field(..., description="User ID (UUID)")
    
    class Config:
        """Pydantic config"""
        schema_extra = {
            "example": {
                "topic": "Climate Change Solutions",
                "user_id": "12345678-1234-1234-1234-123456789012"
            }
        }

class VideoUploadResponse(BaseModel):
    """Response model for video upload"""
    submission_id: str = Field(..., description="Unique submission ID")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Response message")
    files: Optional[Dict[str, str]] = Field(None, description="File URLs")
    
    class Config:
        """Pydantic config"""
        schema_extra = {
            "example": {
                "submission_id": "12345678-1234-1234-1234-123456789012",
                "status": "uploaded",
                "message": "Video uploaded successfully",
                "files": {
                    "original": "minio-url",
                    "video_only": "minio-url",
                    "audio_only": "minio-url"
                }
            }
        }

class VideoStatusResponse(BaseModel):
    """Response model for video status"""
    submission_id: str
    status: str  # uploaded, processing, completed, failed
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class VideoFilesResponse(BaseModel):
    """Response model for video files"""
    submission_id: str
    files: Dict[str, str] = Field(..., description="File URLs")
    original_filename: str
    file_size: int
    topic: str
