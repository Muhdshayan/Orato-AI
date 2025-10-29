from fastapi import APIRouter, HTTPException, Depends
from app.core.database import execute_query
from typing import Dict, Any, Optional
import traceback
import os
import tempfile

# Always use simple ASR service (handles Parakeet subprocess + Google fallback)
from app.services.simple_asr_service import simple_asr_service as asr_service
print("✅ Simple ASR service loaded (Parakeet + Google fallback)")

router = APIRouter()

async def transcribe_in_background(submission_id: str, job_id: str, audio_object: str):
    """Background task to transcribe audio"""
    try:
        print(f"🎤 Starting background transcription for submission: {submission_id}")
        
        # Download audio from MinIO
        from app.services.minio_service import MinIOService
        minio = MinIOService()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            local_audio = os.path.join(tmpdir, f"{submission_id}.wav")
            minio.download_to_file(audio_object, local_audio)
            print(f"✅ Downloaded audio file for transcription")

            # Transcribe
            transcript_data = asr_service.transcribe_audio(local_audio)
            transcript_id = asr_service.store_transcript(submission_id, transcript_data)
            print(f"✅ Transcription completed: {transcript_id}")

        # Update job status to DONE
        from app.core.database import execute_query
        execute_query(
            """
            UPDATE processing_jobs 
            SET status = %s, completed_at = CURRENT_TIMESTAMP
            WHERE job_id = %s
            """,
            ("DONE", job_id)
        )
        print(f"✅ Updated transcription job {job_id} to DONE")

    except Exception as e:
        print(f"❌ Background transcription failed: {e}")
        traceback.print_exc()
        
        # Update job status to FAILED
        try:
            from app.core.database import execute_query
            execute_query(
                """
                UPDATE processing_jobs 
                SET status = %s, error_message = %s, completed_at = CURRENT_TIMESTAMP
                WHERE job_id = %s
                """,
                ("FAILED", str(e), job_id)
            )
        except Exception as update_error:
            print(f"❌ Failed to update error status: {update_error}")

@router.get("/{submission_id}")
async def get_transcript(submission_id: str):
    """
    Get transcript for a video submission.
    
    Args:
        submission_id: The video submission ID
        
    Returns:
        Transcript data including text and timestamps
    """
    try:
        print(f"🔍 Fetching transcript for submission: {submission_id}")
        
        # Get transcript from database
        transcript = asr_service.get_transcript(submission_id)
        
        if not transcript:
            raise HTTPException(
                status_code=404,
                detail="Transcript not found for this submission"
            )
        
        # Extract metadata for compatibility
        asr_metadata = transcript.get("asr_metadata", {})
        
        return {
            "submission_id": submission_id,
            "transcript_id": transcript["transcript_id"],
            "full_text": transcript["full_text"],
            "segment_timestamps": transcript.get("segments", []),
            "audio_duration": asr_metadata.get("audio_duration", 0),
            "model_used": asr_metadata.get("model_used", "Simple ASR"),
            "device_used": asr_metadata.get("device_used", "CPU"),
            "word_count": asr_metadata.get("word_count", len(transcript["full_text"].split())),
            "created_at": transcript["created_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching transcript: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch transcript: {str(e)}"
        )

@router.post("/{submission_id}/generate")
async def generate_transcript(submission_id: str):
    """
    Generate transcript for a submission on demand.
    Returns immediately and processes in background.
    """
    try:
        # Verify audio exists
        audio_object = f"derived/{submission_id}_audio_only.wav"
        from app.services.minio_service import MinIOService
        minio = MinIOService()
        if not minio.file_exists(audio_object):
            raise HTTPException(status_code=404, detail="Derived audio not found for this submission")

        # Check if transcription already exists
        existing = asr_service.get_transcript(submission_id)
        if existing:
            return {
                "submission_id": submission_id, 
                "status": "completed", 
                "transcript_id": existing["transcript_id"],
                "message": "Transcript already exists"
            }

        # Create processing job record
        from app.core.database import execute_query
        import uuid
        job_id = str(uuid.uuid4())
        execute_query(
            """
            INSERT INTO processing_jobs (job_id, submission_id, status, enqueued_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            """,
            (job_id, submission_id, "PROCESSING")
        )
        print(f"✅ Created transcription job: {job_id}")

        # Start background transcription
        from fastapi import BackgroundTasks
        import asyncio
        asyncio.create_task(transcribe_in_background(submission_id, job_id, audio_object))

        return {
            "submission_id": submission_id, 
            "status": "processing", 
            "job_id": job_id,
            "message": "Transcription started in background"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error starting transcription: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to start transcription: {str(e)}")

@router.get("/{submission_id}/status")
async def get_transcript_status(submission_id: str):
    """
    Get transcription status for a video submission.
    Checks processing_jobs table for real-time status.
    """
    try:
        print(f"🔍 Checking transcript status for submission: {submission_id}")
        
        # First check if transcript exists (completed)
        transcript = asr_service.get_transcript(submission_id)
        
        if transcript:
            # Transcript is done
            asr_metadata = transcript.get("asr_metadata", {})
            
            return {
                "submission_id": submission_id,
                "status": "completed",
                "progress": 100,
                "transcript_id": transcript["transcript_id"],
                "created_at": transcript["created_at"],
                "model_used": asr_metadata.get("model_used", "Simple ASR")
            }
        
        # Check processing_jobs table for status
        from app.core.database import execute_query
        job = execute_query(
            """
            SELECT job_id, status, enqueued_at, error_message
            FROM processing_jobs
            WHERE submission_id = %s
            ORDER BY enqueued_at DESC
            LIMIT 1
            """,
            (submission_id,),
            fetch_one=True
        )
        
        if job:
            status_map = {
                "PROCESSING": "processing",
                "QUEUED": "queued",
                "DONE": "completed",
                "FAILED": "failed"
            }
            status = status_map.get(job["status"], "unknown")
            progress = 50 if status == "processing" else (100 if status == "completed" else 0)
            
            return {
                "submission_id": submission_id,
                "status": status,
                "progress": progress,
                "job_id": job["job_id"],
                "enqueued_at": job["enqueued_at"],
                "error_message": job.get("error_message")
            }
        
        # No transcript and no job found
        return {
            "submission_id": submission_id,
            "status": "not_started",
            "progress": 0,
            "message": "Transcription not started yet"
        }
            
    except Exception as e:
        print(f"❌ Error checking transcript status: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check transcript status: {str(e)}"
        )

@router.get("/{submission_id}/text")
async def get_transcript_text(submission_id: str):
    """
    Get only the transcript text (without timestamps) for a video submission.
    
    Args:
        submission_id: The video submission ID
        
    Returns:
        Plain text transcript
    """
    try:
        print(f"🔍 Fetching transcript text for submission: {submission_id}")
        
        # Get transcript from database
        transcript = asr_service.get_transcript(submission_id)
        
        if not transcript:
            raise HTTPException(
                status_code=404,
                detail="Transcript not found for this submission"
            )
        
        # Extract metadata for compatibility
        asr_metadata = transcript.get("asr_metadata", {})
        
        return {
            "submission_id": submission_id,
            "text": transcript["full_text"],
            "audio_duration": asr_metadata.get("audio_duration", 0),
            "created_at": transcript["created_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching transcript text: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch transcript text: {str(e)}"
        )

@router.get("/asr/status")
async def get_asr_status():
    """
    Get ASR service status and model information.
    
    Returns:
        ASR service status and configuration
    """
    try:
        return {
            "asr_ready": asr_service.is_ready(),
            "model_name": asr_service.model_name,
            "device": asr_service.device,
            "asr_type": "nemo" if ASR_AVAILABLE else "simple",
            "status": "ready" if asr_service.is_ready() else "not_ready",
            "features": {
                "word_timestamps": ASR_AVAILABLE,
                "segment_timestamps": ASR_AVAILABLE,
                "basic_transcription": True
            }
        }
        
    except Exception as e:
        print(f"❌ Error checking ASR status: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check ASR status: {str(e)}"
        )
