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

@router.post("/{submission_id}/analyze-speech")
async def analyze_speech(submission_id: str):
    """
    Analyze speech metrics (filler words, fluency) for a transcript
    
    Args:
        submission_id: The video submission ID
        
    Returns:
        Speech analysis results
    """
    try:
        print(f"📊 Starting speech analysis for submission: {submission_id}")
        
        # Get transcript
        transcript = asr_service.get_transcript(submission_id)
        
        if not transcript:
            raise HTTPException(
                status_code=404,
                detail="Transcript not found for this submission"
            )
        
        transcript_id = transcript["transcript_id"]
        
        # Prepare complete transcript data for analysis
        asr_metadata = transcript.get("asr_metadata", {})
        full_text = transcript["full_text"]
        segment_timestamps = transcript.get("segments", [])
        audio_duration = asr_metadata.get("audio_duration", 0)
        # Prefer stored word_count; otherwise derive from text
        word_count = asr_metadata.get("word_count") or len(full_text.split())

        transcript_data = {
            "full_text": full_text,
            "segment_timestamps": segment_timestamps,
            "audio_duration": audio_duration,
            "word_count": word_count
        }
        
        # Analyze and store metrics (filler words + pauses + speech rates)
        from app.services.speech_metrics_service import speech_metrics_service
        
        metrics = speech_metrics_service.analyze_and_store_metrics(
            transcript_id, 
            transcript_data
        )
        
        return {
            "submission_id": submission_id,
            "transcript_id": transcript_id,
            "status": "completed",
            "metrics": {
                "filler_word_count": metrics["filler_word_count"],
                "total_word_count": metrics["total_word_count"],
                "filler_word_percentage": metrics["filler_word_percentage"],
                "fluency_score": metrics["fluency_score"],
                "speech_rate": metrics.get("speech_rate", 0),
                "articulation_rate": metrics.get("articulation_rate", 0),
                "total_pause_time": metrics.get("total_pause_time", 0),
                "pause_count": metrics.get("pause_count", 0),
                "continuity_difference_pct": metrics.get("continuity_difference_pct", 0),
                "continuity_interpretation": metrics.get("continuity_interpretation", "")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error analyzing speech: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze speech: {str(e)}"
        )

@router.get("/{submission_id}/speech-metrics")
async def get_speech_metrics(submission_id: str):
    """
    Get speech metrics for a transcript
    
    Args:
        submission_id: The video submission ID
        
    Returns:
        Speech metrics data
    """
    try:
        print(f"📊 Fetching speech metrics for submission: {submission_id}")
        
        # Get transcript
        transcript = asr_service.get_transcript(submission_id)
        
        if not transcript:
            raise HTTPException(
                status_code=404,
                detail="Transcript not found for this submission"
            )
        
        transcript_id = transcript["transcript_id"]
        
        # Get speech metrics
        from app.services.speech_metrics_service import speech_metrics_service
        from app.services.speech_rate_service import speech_rate_service
        metrics = speech_metrics_service.get_speech_metrics(transcript_id)
        
        if not metrics:
            return {
                "submission_id": submission_id,
                "transcript_id": transcript_id,
                "status": "not_analyzed",
                "message": "Speech metrics not yet analyzed. Click 'Analyze Speech' button."
            }
        
        # Calculate categories for better UI display
        speech_rate = metrics.get("speech_rate", 0)
        articulation_rate = metrics.get("articulation_rate", 0)
        fluency_score = metrics.get("fluency_score", 0)
        
        # Get rate categories
        speech_rate_category = speech_rate_service.categorize_rate(speech_rate)
        articulation_rate_category = speech_rate_service.categorize_rate(articulation_rate)
        speech_rate_label = speech_rate_service.get_rate_label(speech_rate_category)
        articulation_rate_label = speech_rate_service.get_rate_label(articulation_rate_category)
        speech_rate_emoji = speech_rate_service.get_rate_emoji(speech_rate_category)
        articulation_rate_emoji = speech_rate_service.get_rate_emoji(articulation_rate_category)
        
        # Get fluency category
        if fluency_score >= 90:
            fluency_category = "excellent"
            fluency_label = "Excellent"
        elif fluency_score >= 75:
            fluency_category = "good"
            fluency_label = "Good"
        elif fluency_score >= 60:
            fluency_category = "fair"
            fluency_label = "Fair"
        elif fluency_score >= 40:
            fluency_category = "poor"
            fluency_label = "Poor"
        else:
            fluency_category = "needs_improvement"
            fluency_label = "Needs Improvement"
        
        # Get pause categories
        pause_percentage = metrics.get("pause_durations", {}).get("summary", {}).get("pause_percentage", 0) if isinstance(metrics.get("pause_durations"), dict) else 0
        pause_count = metrics.get("pause_count", 0)
        
        # Categorize pause percentage
        # Too few pauses (< 2%) = speaking too fast without breaks
        # Good range (2-10%) = natural rhythm with appropriate breaks
        # Moderate (10-20%) = some excessive pausing
        # Too many (> 20%) = excessive pauses affecting flow
        if pause_percentage < 2:
            pause_percentage_category = "too_few"
            pause_percentage_label = "Too Few Pauses"
            pause_percentage_emoji = "⚡"
        elif pause_percentage < 10:
            pause_percentage_category = "good"
            pause_percentage_label = "Good Control"
            pause_percentage_emoji = "✅"
        elif pause_percentage < 20:
            pause_percentage_category = "moderate"
            pause_percentage_label = "Moderate Pauses"
            pause_percentage_emoji = "⚠️"
        else:
            pause_percentage_category = "high"
            pause_percentage_label = "Too Many Pauses"
            pause_percentage_emoji = "🔴"
        
        # Categorize pause count (based on typical speech patterns)
        # Too few (< 2/min) = speaking too fast, no natural breaks
        # Normal (2-5/min) = natural rhythm with good pacing
        # Moderate (5-10/min) = somewhat frequent but acceptable
        # Frequent (> 10/min) = too many pauses disrupting flow
        audio_duration = transcript.get("asr_metadata", {}).get("audio_duration", 60) if isinstance(transcript.get("asr_metadata"), dict) else 60
        pauses_per_minute = (pause_count / audio_duration * 60) if audio_duration > 0 else 0
        
        if pauses_per_minute < 2:
            pause_count_category = "too_few"
            pause_count_label = "Too Few"
            pause_count_emoji = "⚡"
        elif pauses_per_minute < 5:
            pause_count_category = "normal"
            pause_count_label = "Normal"
            pause_count_emoji = "✅"
        elif pauses_per_minute < 10:
            pause_count_category = "moderate"
            pause_count_label = "Moderate"
            pause_count_emoji = "⚠️"
        else:
            pause_count_category = "high"
            pause_count_label = "Too Frequent"
            pause_count_emoji = "🔴"
        
        return {
            "submission_id": submission_id,
            "transcript_id": transcript_id,
            "status": "completed",
            "filler_word_count": metrics["filler_word_count"],
            "total_word_count": metrics["total_word_count"],
            "filler_word_percentage": metrics["filler_word_percentage"],
            "fluency_score": metrics["fluency_score"],
            "fluency_category": fluency_category,
            "fluency_label": fluency_label,
            "speech_rate": speech_rate,
            "speech_rate_category": speech_rate_category,
            "speech_rate_label": speech_rate_label,
            "speech_rate_emoji": speech_rate_emoji,
            "articulation_rate": articulation_rate,
            "articulation_rate_category": articulation_rate_category,
            "articulation_rate_label": articulation_rate_label,
            "articulation_rate_emoji": articulation_rate_emoji,
            "total_pause_time": metrics.get("total_pause_time", 0),
            "pause_count": metrics.get("pause_count", 0),
            "pause_count_category": pause_count_category,
            "pause_count_label": pause_count_label,
            "pause_count_emoji": pause_count_emoji,
            "pause_percentage": pause_percentage,
            "pause_percentage_category": pause_percentage_category,
            "pause_percentage_label": pause_percentage_label,
            "pause_percentage_emoji": pause_percentage_emoji,
            "pauses_per_minute": round(pauses_per_minute, 1),
            "pause_durations": metrics.get("pause_durations", {}),
            "continuity_difference_pct": metrics.get("continuity_difference_pct", 0),
            "continuity_interpretation": metrics.get("continuity_interpretation", ""),
            "created_at": metrics["created_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching speech metrics: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch speech metrics: {str(e)}"
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
            "model_name": getattr(asr_service, 'model_name', 'nvidia/parakeet-tdt-0.6b-v3'),
            "device": getattr(asr_service, 'device', 'unknown'),
            "asr_type": "simple",
            "status": "ready" if asr_service.is_ready() else "not_ready",
            "features": {
                "word_timestamps": True,
                "segment_timestamps": True,
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
