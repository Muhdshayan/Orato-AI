import asyncio
import logging
import json
from typing import Dict, Any

from app.core.database import execute_query
from app.services.simple_asr_service import simple_asr_service
from app.services.visual_analysis_service import visual_analysis_service
from app.services.speech_metrics_service import speech_metrics_service
from app.services.report_generator_service import report_generator_service
from python_modules.content_relevance import content_relevance_service

logger = logging.getLogger(__name__)

class AnalysisOrchestrator:
    """
    Coordinates the parallel execution of Audio and Video analysis.
    """

    async def process_submission(self, submission_id: str, audio_path: str, video_path: str):
        """
        3-Phase pipeline:
          Phase 1 (parallel) : CV video analysis  +  Transcription (ASR + store + speech metrics)
          Phase 2 (sequential): Content Relevance  — waits for transcription to be done
          Phase 3 (sequential): Generate Analytics — waits for content relevance to be stored
        """
        print(f"🎼 Orchestrator: Starting analysis for {submission_id}")
        self._update_job_status(submission_id, "PROCESSING")

        try:
            # ── Phase 1 & 2: CV and Transcription in PARALLEL FLUID FLOW ─────
            print(f"\n{'='*60}")
            print(f"🎼 Fluid Phasing: ASR and CV starting in parallel")
            print(f"{'='*60}")

            # Define the ASR -> Content Relevance chain
            async def run_speech_logic():
                try:
                    t_id, t_data = await asyncio.to_thread(
                        self._run_transcription_pipeline, submission_id, audio_path
                    )
                    if t_id and t_data:
                        print(f"✅ Transcription Ready. Launching Phase 2 (Content Relevance) immediately.")
                        await asyncio.to_thread(
                            self._run_content_relevance, submission_id, t_id, t_data
                        )
                        return t_id, t_data
                    return None, None
                except Exception as e:
                    print(f"❌ Speech Logic Failed: {e}")
                    raise e

            # Start ASR/CR and CV in parallel
            task_speech = asyncio.create_task(run_speech_logic())
            task_video = asyncio.to_thread(
                self._run_video_pipeline, submission_id, video_path
            )

            # Wait for both distinct paths to finish
            print(f"🎼 Waiting for parallel streams (Speech/CR and CV) to converge...")
            phase1_results = await asyncio.gather(
                task_speech, task_video, return_exceptions=True
            )
            speech_result, video_result = phase1_results

            # Collect results and handle errors
            error_msgs = []
            transcript_id = None
            
            if isinstance(speech_result, Exception):
                print(f"❌ Speech/CR Stream Failed: {speech_result}")
                error_msgs.append(f"Speech/CR: {str(speech_result)}")
            else:
                transcript_id, _ = speech_result
                print(f"✅ Speech/CR Stream complete.")

            if isinstance(video_result, Exception):
                print(f"❌ Video Pipeline Failed: {video_result}")
                error_msgs.append(f"Video: {str(video_result)}")
            else:
                print(f"✅ Video Pipeline complete.")

            # ── Phase 3: Generate Analytics (all prerequisites complete) ──────
            print(f"\n{'='*60}")
            print(f"🎼 Phase 3: Generate Analytics (all prerequisites complete ✓)")
            print(f"{'='*60}")

            try:
                await self._generate_analytics(submission_id, transcript_id)
                print(f"✅ Phase 3 – Analytics generation complete")
            except Exception as analytics_err:
                print(f"⚠️ Phase 3 – Analytics generation failed (non-fatal): {analytics_err}")
                import traceback; traceback.print_exc()

            # ── Final status ──────────────────────────────────────────────────
            if error_msgs:
                combined_error = "; ".join(error_msgs)
                self._update_job_status(submission_id, "FAILED", combined_error)
            else:
                print(f"\n✅ Orchestrator: ALL phases complete for {submission_id}")
                self._update_job_status(submission_id, "DONE")

        except Exception as e:
            print(f"❌ Orchestrator Critical Failure: {e}")
            import traceback; traceback.print_exc()
            self._update_job_status(submission_id, "FAILED", str(e))

    @staticmethod
    def _get_declared_topic(submission_id: str) -> str:
        """Fetch declared_topic from DB for a submission."""
        try:
            rows = execute_query(
                "SELECT declared_topic FROM video_submissions WHERE submission_id = %s",
                (submission_id,),
            )
            print(f"       DEBUG: Query returned {len(rows) if rows else 0} rows, type: {type(rows)}")
            if not rows or len(rows) == 0:
                print(f"       ⚠️ No submission found, using default topic 'General'")
                return "General"
            row = rows[0]
            print(f"       DEBUG: Row data: {row}, type: {type(row)}")
            # Handle both tuple and dict returns
            topic = row[0] if isinstance(row, (tuple, list)) else row.get("declared_topic", "General")
            print(f"       ✅ Got topic: {topic}")
            return topic
        except Exception as e:
            print(f"       ❌ ERROR in _get_declared_topic: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return "General"

    def _run_transcription_pipeline(self, submission_id: str, audio_path: str):
        """
        Phase 1 (audio side):
          Step 1 – Transcribe audio
          Step 2 – Store transcript in DB
          Step 3 – Analyze & store speech metrics
        Returns (transcript_id, transcript_data) so Phase 2 can use them.
        """
        print(f"🎤 Transcription Pipeline starting for {submission_id}...")
        transcript_data = None
        transcript_id = None

        # Step 1 – Transcribe
        print(f"   Step 1: Transcribing audio...")
        try:
            transcript_data = simple_asr_service.transcribe_audio(audio_path)
            print(f"   ✅ Step 1 complete – transcription done")
        except Exception as te:
            print(f"   ⚠️ Step 1 failed: {te} – using empty transcript")
            transcript_data = {"full_text": "", "text": "", "segments": []}

        # Step 2 – Store transcript (only if we have text)
        full_text = (transcript_data or {}).get("full_text") or (transcript_data or {}).get("text", "")
        if full_text.strip():
            print(f"   Step 2: Storing transcript...")
            transcript_id = simple_asr_service.store_transcript(submission_id, transcript_data)
            print(f"   ✅ Step 2 complete – transcript_id={transcript_id}")
        else:
            print(f"   ⚠️ Step 2 skipped – no transcript text to store")

        # Step 3 – Speech metrics (only if transcript was stored)
        if transcript_id:
            print(f"   Step 3: Analyzing speech metrics...")
            speech_metrics_service.analyze_and_store_metrics(transcript_id, transcript_data)
            print(f"   ✅ Step 3 complete – speech metrics stored")
        else:
            print(f"   ⚠️ Step 3 skipped – no transcript_id")

        print(f"✅ Transcription Pipeline finished (transcript_id={transcript_id})")
        return (transcript_id, transcript_data)

    def _run_content_relevance(self, submission_id: str, transcript_id: str, transcript_data: dict):
        """
        Phase 2: Run content relevance analysis.
        Called ONLY after transcription is confirmed done and transcript_id is in the DB.
        """
        print(f"📚 Content Relevance: starting for transcript_id={transcript_id}")
        declared_topic = self._get_declared_topic(submission_id)
        full_text = (transcript_data or {}).get("full_text") or (transcript_data or {}).get("text", "")
        print(f"   Topic: {declared_topic!r}  |  Text length: {len(full_text)} chars")

        if not full_text.strip():
            print(f"   ⚠️ No transcript text – content relevance will run with empty input")

        result = content_relevance_service.analyze_and_store(transcript_id, full_text, declared_topic)
        print(f"   ✅ Content Relevance stored: topic_match={result.get('topic_match_score')}, "
              f"factual={result.get('factual_accuracy')}, overall={result.get('overall_content_score')}")
        return result

    async def _generate_analytics(self, submission_id: str, transcript_id: str):
        """
        Phase 3: Final analytics generation step.
        Runs after content relevance is completed and stored.
        Uses ReportGeneratorService to aggregate scores and generate LLM feedback.
        """
        print(f"📊 Generate Analytics: triggering report generation for {submission_id}...")

        try:
            # The service handles aggregation, weighting, and LLM advice
            report = await report_generator_service.generate_report(submission_id)
            
            print(f"   Final Overall Score: {report.get('overall_score')}")
            print(f"✅ Analytics generation complete for {submission_id}")

        except Exception as e:
            print(f"   ⚠️ Analytics aggregation error (non-fatal): {type(e).__name__}: {e}")
            import traceback; traceback.print_exc()



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