import os
import uuid
import tempfile
from typing import Dict, Any
from app.core.database import execute_query
from app.services.minio_service import MinIOService
from app.core.config import settings

# Video processing functions (copied from python_modules for self-contained backend)
from moviepy.editor import VideoFileClip
import speech_recognition as sr
from langdetect import detect, LangDetectException

class VideoService:
    """Service class for video processing operations"""
    
    def __init__(self):
        """Initialize video service with MinIO client"""
        self.minio = MinIOService()
        self.max_duration_seconds = settings.MAX_DURATION_SECONDS
        self.supported_language = settings.SUPPORTED_LANGUAGE
    
    async def upload_video(
        self, 
        file_path: str, 
        topic: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """Upload video and start processing (legacy method - now uses background processing)"""
        
        # Generate submission ID
        import uuid
        submission_id = str(uuid.uuid4())
        
        # Process video (separate audio/video and create database record)
        try:
            print(f"🚀 Starting video processing for user: {user_id}")
            self._process_video_file(file_path, submission_id, topic, user_id)
            print(f"✅ Video processing completed: {submission_id}")
        except Exception as e:
            print(f"❌ Video processing failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Get file URLs with error handling
        try:
            print(f"🔍 Generating presigned URLs for submission: {submission_id}")
            files = {
                "original": self.minio.get_presigned_url(f"uploads/{submission_id}.mp4"),
                "video_only": self.minio.get_presigned_url(f"derived/{submission_id}_video_only.mp4"),
                "audio_only": self.minio.get_presigned_url(f"derived/{submission_id}_audio_only.wav")
            }
            print(f"✅ Generated presigned URLs successfully")
        except Exception as e:
            print(f"⚠️ Failed to generate presigned URLs: {e}")
            # Return without file URLs if presigned URL generation fails
            files = None
        
        response = {
            "submission_id": submission_id,
            "status": "completed",
            "message": "Video processed successfully"
        }
        
        if files:
            response["files"] = files
        else:
            response["message"] += " (Files uploaded to MinIO, URLs available via status endpoint)"
        
        return response
    
    def process_video_background(self, video_path: str, submission_id: str, topic: str, user_id: str):
        """
        Background task to process video without blocking the API response.
        Updates the database entry that was already created.
        """
        try:
            print(f"🎬 Background processing started for submission {submission_id}")
            
            # Call the existing video processing logic
            result = self._process_video_file(video_path, submission_id, topic, user_id)
            
            print(f"✅ Background processing completed for submission {submission_id}")
            
        except Exception as e:
            print(f"❌ Background processing failed for submission {submission_id}: {e}")
            import traceback
            traceback.print_exc()
            
            # Update status to failed
            try:
                self._update_status(submission_id, "failed")
                execute_query(
                    "UPDATE processing_jobs SET status = %s, error_message = %s WHERE submission_id = %s",
                    ("FAILED", str(e), submission_id)
                )
            except Exception as update_error:
                print(f"❌ Failed to update error status: {update_error}")
        
        finally:
            # Cleanup temp file
            try:
                if os.path.exists(video_path):
                    os.unlink(video_path)
                    print(f"🧹 Cleaned up temp file: {video_path}")
            except Exception as cleanup_error:
                print(f"⚠️ Failed to cleanup temp file: {cleanup_error}")
    
    
    def _update_status(self, submission_id: str, status: str, error_message: str = None):
        """Update processing status in database"""
        query = """
        UPDATE video_submissions 
        SET status = %s 
        WHERE submission_id = %s
        """
        execute_query(query, (status, submission_id))
        
        if error_message:
            print(f"❌ Processing failed: {error_message}")
        else:
            print(f"✅ Status updated to: {status}")
    
    def _create_processing_job(self, submission_id: str, status: str = 'QUEUED', error_message: str = None):
        """Create a processing job entry in the database"""
        query = """
        INSERT INTO processing_jobs (submission_id, status, error_message)
        VALUES (%s, %s, %s)
        RETURNING job_id
        """
        result = execute_query(query, (submission_id, status, error_message), fetch_one=True)
        job_id = result["job_id"] if result else str(uuid.uuid4())
        print(f"✅ Created processing job: {job_id} with status: {status}")
        return job_id
    
    def _update_processing_job(self, submission_id: str, status: str, error_message: str = None):
        """Update processing job status in database"""
        query = """
        UPDATE processing_jobs 
        SET status = %s, completed_at = CURRENT_TIMESTAMP, error_message = %s
        WHERE submission_id = %s
        """
        execute_query(query, (status, error_message, submission_id))
        print(f"✅ Processing job updated to: {status}")
    
    async def get_status(self, submission_id: str) -> Dict[str, Any]:
        """Get video processing status"""
        query = """
        SELECT submission_id, status, created_at, uploaded_at
        FROM video_submissions 
        WHERE submission_id = %s
        """
        result = execute_query(query, (submission_id,), fetch_one=True)
        
        if not result:
            return {"error": "Submission not found"}
        
        # Calculate progress based on status
        status = result["status"]
        if status == "uploaded":
            progress = 20
        elif status == "processing":
            progress = 50
        elif status == "completed":
            progress = 100
        elif status == "failed":
            progress = 0
        else:
            progress = 10
        
        return {
            "submission_id": result["submission_id"],
            "status": status,
            "progress": progress,
            "created_at": result["created_at"],
            "completed_at": result["uploaded_at"] if status == "completed" else None
        }
    
    def _process_video_file(self, video_path: str, submission_id: str, declared_topic: str, user_id: str) -> str:
        """Process video file: split into audio/video and upload to MinIO"""
        
        print(f"🔍 Processing video for submission: {submission_id}")
        print(f"🔍 Processing video for user_id: {user_id}")
        print(f"🔍 Video path: {video_path}")
        print(f"🔍 Video exists: {os.path.exists(video_path)}")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"File not found: {video_path}")

        # Create temporary directory for processing
        import tempfile
        temp_dir = tempfile.mkdtemp()
        print(f"🔍 Using temp directory: {temp_dir}")
        
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_video_path = os.path.join(temp_dir, f"{base_name}_video_only.mp4")
        output_audio_path = os.path.join(temp_dir, f"{base_name}_audio_only.wav")

        # 1) Load video and validate duration
        clip = VideoFileClip(video_path)
        try:
            print(f"🔍 Video duration: {clip.duration:.2f}s")
            if clip.duration > self.max_duration_seconds:
                raise ValueError(
                    f"Video duration ({clip.duration:.2f}s) exceeds limit of {self.max_duration_seconds}s"
                )

            # 2) Language quick check via SpeechRecognition + langdetect on a short subclip
            sample_audio_path = os.path.join(temp_dir, f"{base_name}_langcheck.wav")
            audio_for_check = clip.audio
            if audio_for_check is None:
                raise ValueError("Video has no audio track")

            sample_end = min(15, clip.duration)
            audio_for_check.subclip(0, sample_end).write_audiofile(sample_audio_path, verbose=False, logger=None)

            recognizer = sr.Recognizer()
            with sr.AudioFile(sample_audio_path) as source:
                audio_data = recognizer.record(source)

            detected_lang = None
            try:
                transcribed_text = recognizer.recognize_google(audio_data)
                detected_lang = detect(transcribed_text)
                if detected_lang != self.supported_language:
                    raise ValueError(f"Detected language '{detected_lang}' != '{self.supported_language}'")
            except (sr.UnknownValueError, sr.RequestError, LangDetectException):
                # proceed but warn
                pass
            finally:
                if os.path.exists(sample_audio_path):
                    os.remove(sample_audio_path)

            # 3) Split into video (no audio) and audio-only wav
            print(f"🔍 Writing video file: {output_video_path}")
            clip.write_videofile(
                output_video_path, 
                audio=False, 
                verbose=False, 
                logger=None
            )
            print(f"✅ Video file written successfully")
            
            print(f"🔍 Writing audio file: {output_audio_path}")
            clip.audio.write_audiofile(
                output_audio_path, 
                verbose=False, 
                logger=None
            )
            print(f"✅ Audio file written successfully")

        finally:
            clip.close()

        # 4) Use provided submission ID for MinIO object names
        original_obj = f"uploads/{submission_id}.mp4"
        video_only_obj = f"derived/{submission_id}_video_only.mp4"
        audio_only_obj = f"derived/{submission_id}_audio_only.wav"

        print(f"🔍 Uploading original video to MinIO: {original_obj}")
        # Upload original video
        self.minio.upload_file(video_path, original_obj, content_type="video/mp4")
        print(f"✅ Original video uploaded to MinIO")
        
        print(f"🔍 Uploading derived video to MinIO: {video_only_obj}")
        # Upload derived files
        self.minio.upload_file(output_video_path, video_only_obj, content_type="video/mp4")
        print(f"✅ Derived video uploaded to MinIO")
        
        print(f"🔍 Uploading derived audio to MinIO: {audio_only_obj}")
        self.minio.upload_file(output_audio_path, audio_only_obj, content_type="audio/wav")
        print(f"✅ Derived audio uploaded to MinIO")

        # 5) Update database entry with MinIO details
        print(f"🔍 Updating database entry for submission: {submission_id}")
        conn = self._get_pg_conn()
        try:
            # Update the existing database entry with file details
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE video_submissions 
                    SET filename = %s, filesize = %s, minio_bucket = %s, minio_object_name = %s
                    WHERE submission_id = %s
                    """,
                    (os.path.basename(video_path), os.path.getsize(video_path), 
                     settings.MINIO_MEDIA_BUCKET, original_obj, submission_id)
                )
                conn.commit()
            print(f"✅ Updated submission: {submission_id}")
            print(f"🔍 Database update successful, video separation complete!")
            
            db_submission_id = submission_id  # Use the same ID
            
            # Create processing job
            job_id = self._create_processing_job(db_submission_id, "PROCESSING")
            
            # Update status to completed - video separation is done
            self._update_status(db_submission_id, "completed")
            self._update_processing_job(db_submission_id, "DONE")
            print(f"✅ Video separation completed successfully: {db_submission_id}")
            
            # NOTE: Transcription is now manual via the "Transcribe Audio" button
            # It will be triggered by POST /api/v1/transcripts/{submission_id}/generate
            
            return db_submission_id  # Return the database submission_id for file URLs
        except Exception as e:
            # Update status to failed if something goes wrong
            if 'db_submission_id' in locals():
                self._update_status(db_submission_id, "failed")
                self._update_processing_job(db_submission_id, "FAILED", str(e))
            raise
        finally:
            conn.close()
        
        # Cleanup temporary files
        try:
            import shutil
            shutil.rmtree(temp_dir)
            print(f"🧹 Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            print(f"⚠️ Failed to cleanup temp directory: {e}")
    
    def _get_pg_conn(self):
        """Get PostgreSQL connection"""
        import psycopg2
        return psycopg2.connect(
            host=settings.PGHOST,
            port=settings.PGPORT,
            user=settings.PGUSER,
            password=settings.PGPASSWORD,
            database=settings.PGDATABASE
        )
    
    def _insert_video_submission(self, conn, submission_id: str, user_id: str, filename: str, filesize: int, 
                                declared_topic: str, minio_bucket: str, minio_object_name: str):
        """Insert video submission record into database with specified submission_id"""
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO video_submissions (submission_id, user_id, filename, filesize, declared_topic, minio_object_name, minio_bucket)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING submission_id
                """,
                (submission_id, user_id, filename, filesize, declared_topic, minio_object_name, minio_bucket),
            )
            row = cur.fetchone()
            conn.commit()
            return row["submission_id"]
