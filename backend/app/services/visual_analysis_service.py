import os
import json
import logging
import traceback
from typing import Dict, Any, Optional

# Database & Config
from app.core.database import execute_query
from app.core.config import settings

# MinIO to download video if missing
from app.services.minio_service import MinIOService

# Import the CV Engine
try:
    from app.services.cv_engine.body_language_analyzer import analyze_video
    CV_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ CV Engine not available: {e}")
    CV_AVAILABLE = False

class VisualAnalysisService:
    """
    Service to orchestrate Body Language Analysis.
    Handles file retrieval, analysis execution, and database storage.
    """
    
    def __init__(self):
        self.minio = MinIOService()
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.temp_dir = os.path.join(self.project_root, '.cache', 'temp')
        os.makedirs(self.temp_dir, exist_ok=True)

    def analyze_submission(self, submission_id: str, video_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Run visual analysis on a video submission.
        """
        if not CV_AVAILABLE:
            raise RuntimeError("Computer Vision modules are not installed/loaded.")

        print(f"👁️ Starting Visual Analysis for: {submission_id}")

        # 1. Determine Video Path
        if video_path and os.path.exists(video_path):
            print(f"📂 Using provided local video path: {video_path}")
        else:
            video_path = self._get_local_video_path(submission_id)
        
        if not video_path or not os.path.exists(video_path):
            raise FileNotFoundError(f"Could not locate video file for {submission_id}")

        try:
            # 2. Run the Analysis (The Heavy Lifting)
            print(f"🏃 Running CV Pipeline on: {video_path}")
            
            analysis_result = analyze_video(
                video_path=video_path, 
                output_path=None, 
                annotate=False
            )
            
            # 3. Store result in Database
            self._store_result(submission_id, analysis_result)
            
            return analysis_result

        except Exception as e:
            print(f"❌ Visual Analysis Failed: {e}")
            traceback.print_exc()
            raise e

    def _get_local_video_path(self, submission_id: str) -> Optional[str]:
        """Finds or downloads the video file."""
        query = "SELECT minio_object_name, filename FROM video_submissions WHERE submission_id = %s"
        record = execute_query(query, (submission_id,), fetch_one=True)
        
        if not record:
            return None

        minio_path = record['minio_object_name']
        filename = record['filename']
        local_path = os.path.join(self.temp_dir, f"{submission_id}_{filename}")

        if os.path.exists(local_path):
            return local_path

        print(f"⬇️ Downloading video from MinIO: {minio_path}")
        try:
            self.minio.client.fget_object(
                settings.MINIO_MEDIA_BUCKET,
                minio_path,
                local_path
            )
            return local_path
        except Exception as e:
            print(f"❌ MinIO Download failed: {e}")
            return None

    def _store_result(self, submission_id: str, data: Dict[str, Any]):
        """Maps CV Engine output to the Postgres Schema."""
        print(f"💾 Mapping CV results to Database Schema...")

        try:
            # 1. Create Artifact (Summary of the whole video)
            # IMPORTANT: We store the FULL JSON result in 'keypoints_json' so the frontend 
            # can retrieve all details (feedback, ratings, etc.) easily.
            full_result_json = json.dumps(data)
            
            artifact_query = """
            INSERT INTO cv_artifacts (submission_id, frame_index, keypoints_json)
            VALUES (%s, %s, %s)
            RETURNING artifact_id
            """
            
            # We use frame_index 0 to represent the "Whole Video Analysis Report"
            artifact_result = execute_query(
                artifact_query, 
                (submission_id, 0, full_result_json), 
                fetch_one=True
            )
            artifact_id = artifact_result['artifact_id']

            # 2. Insert Posture Metrics (For querying/analytics)
            posture = data.get('posture', {})
            head = data.get('head_pose', {})
            
            posture_query = """
            INSERT INTO posture_metrics (
                artifact_id, slouch_duration, head_orientation, shoulder_alignment, posture_score
            ) VALUES (%s, %s, %s, %s, %s)
            """
            
            slouch_pct = posture.get('slouch_duration', {}).get('slouch_percentage', 0)
            head_yaw = head.get('yaw', {}).get('mean', 0)
            posture_score = data.get('overall_score', 0) 
            
            execute_query(posture_query, (artifact_id, slouch_pct, head_yaw, 0.0, posture_score))

            # 3. Insert Gesture Metrics (For querying/analytics)
            gestures = data.get('gestures', {})
            
            gesture_query = """
            INSERT INTO gesture_metrics (
                artifact_id, hand_gesture_count, gesture_velocity, movement_consistency, gesture_score
            ) VALUES (%s, %s, %s, %s, %s)
            """
            
            freq = gestures.get('gesture_frequency', {}).get('gestures_per_minute', 0)
            duration = data.get('video_metadata', {}).get('duration_seconds', 1)
            count = int(freq * (duration / 60))
            consistency = data.get('motion_energy', {}).get('consistency_score', 0)
            
            execute_query(gesture_query, (artifact_id, count, 0.0, consistency, 0.0))

            print("✅ CV Data successfully mapped to database.")

        except Exception as e:
            print(f"❌ Database Mapping Failed: {e}")
            raise e

    def get_analysis_result(self, submission_id: str) -> Optional[Dict]:
        """
        Retrieve the full analysis JSON from the database.
        We look for the 'summary artifact' (frame_index=0) in cv_artifacts table.
        """
        try:
            # We fetch the full JSON blob we saved in _store_result
            query = """
            SELECT keypoints_json 
            FROM cv_artifacts 
            WHERE submission_id = %s AND frame_index = 0
            ORDER BY created_at DESC
            LIMIT 1
            """
            result = execute_query(query, (submission_id,), fetch_one=True)
            
            if result and result['keypoints_json']:
                # Postgres JSONB driver usually returns a dict automatically.
                # If it's a string, we parse it.
                data = result['keypoints_json']
                return json.loads(data) if isinstance(data, str) else data
            
            return None
            
        except Exception as e:
            print(f"❌ Failed to retrieve analysis result: {e}")
            return None

visual_analysis_service = VisualAnalysisService()