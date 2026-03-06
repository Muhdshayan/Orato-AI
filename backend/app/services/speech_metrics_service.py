"""
Speech Metrics Service
Handles speech analysis metrics (filler words, fluency score, pauses, speech rate)
"""
from typing import Dict, Any, Optional, List
import json
import math
from app.core.database import execute_query
from python_modules.nlp_asr.filler_word_service import filler_word_service
from python_modules.nlp_asr.pause_detection_service import pause_detection_service
from python_modules.nlp_asr.speech_rate_service import speech_rate_service

class SpeechMetricsService:
    """Service for analyzing and storing speech quality metrics"""
    
    def analyze_and_store_metrics(self, transcript_id: str, transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze transcript for filler words, pauses, and speech rates.
        Generates time-series data for frontend visualization.
        """
        try:
            print(f"📊 Analyzing speech metrics for transcript: {transcript_id}")
            
            # --- 1. DATA PREPARATION & SAFETY CHECKS ---
            full_text = transcript_data.get('full_text', '')
            # Handle different key names from different parsers
            segments = transcript_data.get('segments') or transcript_data.get('segment_timestamps') or []
            
            # CRITICAL FIX: Calculate Duration Fallback
            # Prevents the "16000 WPM" bug by ensuring duration is never 0
            audio_duration = transcript_data.get('audio_duration', 0)
            if not audio_duration and transcript_data.get('asr_metadata'):
                audio_duration = transcript_data['asr_metadata'].get('audio_duration', 0)
                
            if (audio_duration is None or audio_duration <= 0.1) and segments:
                # Use the end time of the last segment
                last_seg = segments[-1]
                if isinstance(last_seg, dict):
                    audio_duration = last_seg.get('end', 0)
                elif isinstance(last_seg, (list, tuple)) and len(last_seg) >= 2:
                    audio_duration = last_seg[1]
                print(f"⚠️ Duration missing. Calculated from segments: {audio_duration}s")
            
            # Clamp to minimum 1s to prevent division by zero
            if audio_duration <= 0: audio_duration = 1 
            
            word_count = transcript_data.get('word_count', len(full_text.split()))
            
            # --- Step 1: Analyze filler words ---
            print(f"   Analyzing filler words...")
            try:
                filler_analysis = filler_word_service.detect_fillers({
                    'full_text': full_text,
                    'word_timestamps': [],
                    'audio_duration': audio_duration
                })
                filler_count = filler_analysis.get('filler_word_count', 0)
                total_words = filler_analysis.get('total_words', word_count)
                filler_percentage = filler_analysis.get('filler_percentage', 0)
                fluency_score = filler_analysis.get('fluency_score', 0)
            except Exception as e:
                print(f"⚠️ Filler analysis warning: {e}")
                filler_count = 0
                total_words = word_count
                filler_percentage = 0
                fluency_score = 0

            # --- Step 2: Analyze pauses ---
            print(f"   Analyzing pauses...")
            try:
                pause_analysis = pause_detection_service.detect_pauses(segments, audio_duration)
                pause_summary = pause_analysis.get('summary', {'total_pause_time': 0, 'pause_count': 0})
                pauses = pause_analysis.get('pauses', [])
            except Exception as e:
                print(f"⚠️ Pause analysis warning: {e}")
                pause_summary = {'total_pause_time': 0, 'pause_count': 0}
                pauses = []
            
            # --- Step 3: Calculate speech rates ---
            print(f"   Calculating global rates...")
            # Manual calculation to ensure mathematical safety
            minutes = audio_duration / 60.0
            speech_rate = round(word_count / minutes) if minutes > 0 else 0
            
            speaking_time = audio_duration - pause_summary.get('total_pause_time', 0)
            speaking_minutes = speaking_time / 60.0
            articulation_rate = round(word_count / speaking_minutes) if speaking_minutes > 0 else 0
            
            print(f"   ✓ Speech rate: {speech_rate} WPM")

            # --- Step 4: Generate Timeline (THE COOL GRAPH DATA) ---
            # This generates the array of [time, wpm] points needed for the EKG chart
            pace_timeline = self._calculate_rolling_pace(segments, audio_duration)

            # --- Step 5: Store in DB ---
            # We pack the new timeline into the existing JSON column
            extended_metrics = {
                'pauses': pauses,
                'summary': pause_summary,
                'pace_timeline': pace_timeline 
            }
            
            # Continuity calculation
            diff_pct = 0
            if articulation_rate > 0:
                diff_pct = ((articulation_rate - speech_rate) / articulation_rate) * 100

            query = """
            INSERT INTO speech_metrics (
                transcript_id, filler_word_count, total_word_count, filler_word_percentage,
                fluency_score, speech_rate, articulation_rate, total_pause_time,
                pause_count, pause_durations, articulation_score, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING metrics_id
            """
            
            result = execute_query(
                query,
                (
                    transcript_id, filler_count, total_words, filler_percentage,
                    fluency_score, speech_rate, articulation_rate,
                    pause_summary.get('total_pause_time', 0), pause_summary.get('pause_count', 0),
                    json.dumps(extended_metrics), diff_pct
                ),
                fetch_one=True
            )
            
            metrics_id = result['metrics_id']
            print(f"✅ Speech metrics stored with ID: {metrics_id}")
            
            # Return complete dictionary (Prevents KeyError in API)
            return {
                'metrics_id': metrics_id,
                'transcript_id': transcript_id,
                'filler_word_count': filler_count,
                'total_word_count': total_words,
                'filler_word_percentage': filler_percentage,
                'fluency_score': fluency_score,
                'speech_rate': speech_rate,
                'articulation_rate': articulation_rate,
                'total_pause_time': pause_summary.get('total_pause_time', 0),
                'pause_count': pause_summary.get('pause_count', 0),
                'pace_timeline': pace_timeline, # Vital for frontend
                'pause_durations': extended_metrics,
                'continuity_difference_pct': diff_pct,
                'continuity_interpretation': "Calculated"
            }
            
        except Exception as e:
            print(f"❌ Metrics Error: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _calculate_rolling_pace(self, segments: List[Dict], duration: float) -> List[Dict]:
        """
        Generates 5-second buckets of WPM for the timeline graph.
        Returns: List of {time: seconds, wpm: int}
        """
        # Safety check
        if not segments or duration <= 0: 
            print("⚠️ No segments or duration for timeline calculation.")
            return []
        
        # Bucket size in seconds
        step = 5 
        # Create buckets covering the whole duration
        num_buckets = int(math.ceil(duration / step)) + 1
        buckets = [0] * num_buckets
        
        for seg in segments:
            # Handle dictionary vs list format from different ASR parsers
            if isinstance(seg, dict):
                start = seg.get('start', 0)
                text = seg.get('text', '')
            elif isinstance(seg, (list, tuple)) and len(seg) >= 3:
                start = seg[1]
                text = seg[0]
            else:
                continue 
            
            # Find which 5s bucket this segment starts in
            idx = int(start / step)
            if idx < len(buckets):
                # Add word count to that bucket
                buckets[idx] += len(text.split())
        
        # Convert word counts to WPM
        timeline = []
        for i, count in enumerate(buckets):
            time_point = i * step
            if time_point > duration: break
            
            # Formula: (Words in 5s) * (60s / 5s) = WPM
            wpm = count * (60 / step)
            
            timeline.append({
                'time': time_point,
                'wpm': round(wpm)
            })
            
        print(f"✅ Generated {len(timeline)} timeline points for graph.")
        return timeline
    
    def get_speech_metrics(self, transcript_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve speech metrics including timeline data"""
        query = """
        SELECT * FROM speech_metrics 
        WHERE transcript_id = %s 
        ORDER BY created_at DESC LIMIT 1
        """
        result = execute_query(query, (transcript_id,), fetch_one=True)
        
        if result:
            # Parse JSON to get the timeline
            meta = result['pause_durations']
            if isinstance(meta, str):
                meta = json.loads(meta)
            elif meta is None:
                meta = {}
                
            return {
                **result,
                'pace_timeline': meta.get('pace_timeline', []), # Expose the new graph data
                'pause_durations': meta
            }
        return None

speech_metrics_service = SpeechMetricsService()