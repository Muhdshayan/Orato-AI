import asyncio
import logging
import json
from typing import Dict, Any

from app.core.database import execute_query
from app.services.simple_asr_service import simple_asr_service
from app.services.visual_analysis_service import visual_analysis_service
from app.services.speech_metrics_service import speech_metrics_service

logger = logging.getLogger(__name__)

class AnalysisOrchestrator:
    """
    Coordinates the parallel execution of Audio and Video analysis.
    """

    async def process_submission(self, submission_id: str, audio_path: str, video_path: str):
        """
        Runs ASR and CV Analysis in parallel.
        """
        print(f"🎼 Orchestrator: Starting parallel analysis for {submission_id}")
        self._update_job_status(submission_id, "PROCESSING")

        try:
            # Run tasks in parallel threads to avoid blocking
            task_audio = asyncio.to_thread(self._run_audio_pipeline, submission_id, audio_path)
            task_video = asyncio.to_thread(self._run_video_pipeline, submission_id, video_path)

            # Wait for both
            results = await asyncio.gather(task_audio, task_video, return_exceptions=True)
            audio_result, video_result = results

            # Log errors
            failed = False
            error_msgs = []

            if isinstance(audio_result, Exception):
                print(f"❌ Audio Pipeline Failed: {audio_result}")
                error_msgs.append(f"Audio: {str(audio_result)}")
                failed = True
            
            if isinstance(video_result, Exception):
                print(f"❌ Video Pipeline Failed: {video_result}")
                error_msgs.append(f"Video: {str(video_result)}")
                failed = True

            if failed:
                 # ✅ FIX: Changed 'PARTIAL_FAILURE' to 'FAILED' to match DB constraint
                 combined_error = "; ".join(error_msgs)
                 self._update_job_status(submission_id, "FAILED", combined_error)
            else:
                print(f"✅ Orchestrator: All analysis complete for {submission_id}")
                self._update_job_status(submission_id, "DONE")

        except Exception as e:
            print(f"❌ Orchestrator Critical Failure: {e}")
            self._update_job_status(submission_id, "FAILED", str(e))

    def _run_audio_pipeline(self, submission_id: str, audio_path: str):
        print(f"🎤 Starting Audio Pipeline...")
        # 1. Transcribe
        transcript_data = simple_asr_service.transcribe_audio(audio_path)
        # 2. Store
        transcript_id = simple_asr_service.store_transcript(submission_id, transcript_data)
        # 3. Metrics
        speech_metrics_service.analyze_and_store_metrics(transcript_id, transcript_data)
        print(f"✅ Audio Pipeline Finished.")
        return transcript_id

    def _run_video_pipeline(self, submission_id: str, video_path: str):
        print(f"👁️ Starting Video Pipeline...")
        # This calls the VisualAnalysisService which handles DB storage
        # ✅ FIX: Now passing video_path correctly matches the updated Service
        result = visual_analysis_service.analyze_submission(submission_id, video_path)
        print(f"✅ Video Pipeline Finished.")
        return result

    def _update_job_status(self, submission_id: str, status: str, error_message: str = None):
        query = """
        UPDATE processing_jobs 
        SET status = %s, completed_at = CURRENT_TIMESTAMP, error_message = %s
        WHERE submission_id = %s
        """
        execute_query(query, (status, error_message, submission_id))

analysis_orchestrator = AnalysisOrchestrator()