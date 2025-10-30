"""
Speech Metrics Service
Handles speech analysis metrics (filler words, fluency score, pauses, speech rate)
"""
from typing import Dict, Any, Optional
import json
from app.core.database import execute_query
from app.services.filler_word_service import filler_word_service
from app.services.pause_detection_service import pause_detection_service
from app.services.speech_rate_service import speech_rate_service

class SpeechMetricsService:
    """Service for analyzing and storing speech quality metrics"""
    
    def analyze_and_store_metrics(self, transcript_id: str, transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze transcript for filler words, pauses, and speech rates
        
        Args:
            transcript_id: UUID of the transcript
            transcript_data: Dictionary containing:
                - full_text: Complete transcript text
                - segment_timestamps: List of segments with timestamps
                - audio_duration: Duration in seconds
                - word_count: Total number of words
        
        Returns:
            Dictionary with complete analysis results
        """
        try:
            print(f"📊 Analyzing speech metrics for transcript: {transcript_id}")
            
            # Check if metrics already exist
            existing = self.get_speech_metrics(transcript_id)
            if existing:
                print(f"✅ Metrics already exist, returning existing data")
                return existing
            
            full_text = transcript_data.get('full_text', '')
            segment_timestamps = transcript_data.get('segment_timestamps', [])
            audio_duration = transcript_data.get('audio_duration', 0)
            word_count = transcript_data.get('word_count', len(full_text.split()))
            
            # Step 1: Analyze filler words
            print(f"   Analyzing filler words...")
            filler_analysis = filler_word_service.detect_fillers({
                'full_text': full_text,
                'word_timestamps': [],
                'audio_duration': audio_duration
            })
            
            filler_count = filler_analysis['filler_word_count']
            total_words = filler_analysis['total_words']
            filler_percentage = filler_analysis['filler_percentage']
            fluency_score = filler_analysis['fluency_score']
            
            print(f"   ✓ Filler words: {filler_count}/{total_words} ({filler_percentage}%)")
            print(f"   ✓ Fluency score: {fluency_score}/100")
            
            # Step 2: Analyze pauses
            print(f"   Analyzing pauses...")
            pause_analysis = pause_detection_service.detect_pauses(
                segment_timestamps,
                audio_duration
            )
            
            pause_summary = pause_analysis['summary']
            pauses = pause_analysis['pauses']
            
            print(f"   ✓ Pauses detected: {pause_summary['pause_count']}")
            print(f"   ✓ Total pause time: {pause_summary['total_pause_time']}s")
            
            # Step 3: Calculate speech rates
            print(f"   Calculating speech rates...")
            rate_analysis = speech_rate_service.calculate_rates(
                word_count,
                audio_duration,
                pause_summary['total_pause_time']
            )
            
            speech_rate = rate_analysis['speech_rate']
            articulation_rate = rate_analysis['articulation_rate']
            
            print(f"   ✓ Speech rate: {speech_rate} WPM ({rate_analysis['speech_rate_category']})")
            print(f"   ✓ Articulation rate: {articulation_rate} WPM ({rate_analysis['articulation_rate_category']})")
            
            # Prepare pause_durations JSONB data
            pause_durations_json = {
                'threshold': 0.2,
                'pauses': pauses,
                'summary': pause_summary
            }
            
            # Store all metrics in database
            query = """
            INSERT INTO speech_metrics (
                transcript_id,
                filler_word_count,
                total_word_count,
                filler_word_percentage,
                fluency_score,
                speech_rate,
                articulation_rate,
                total_pause_time,
                pause_count,
                pause_durations,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING metrics_id
            """
            
            result = execute_query(
                query,
                (
                    transcript_id,
                    filler_count,
                    total_words,
                    filler_percentage,
                    fluency_score,
                    speech_rate,
                    articulation_rate,
                    pause_summary['total_pause_time'],
                    pause_summary['pause_count'],
                    json.dumps(pause_durations_json)
                ),
                fetch_one=True
            )
            
            metrics_id = result['metrics_id']
            print(f"✅ Speech metrics stored with ID: {metrics_id}")
            
            return {
                'metrics_id': metrics_id,
                'transcript_id': transcript_id,
                'filler_word_count': filler_count,
                'total_word_count': total_words,
                'filler_word_percentage': round(filler_percentage, 2),
                'fluency_score': round(fluency_score, 2),
                'speech_rate': round(speech_rate, 2),
                'articulation_rate': round(articulation_rate, 2),
                'total_pause_time': pause_summary['total_pause_time'],
                'pause_count': pause_summary['pause_count'],
                'pause_summary': pause_summary
            }
            
        except Exception as e:
            print(f"❌ Failed to analyze/store speech metrics: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def get_speech_metrics(self, transcript_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve speech metrics for a transcript
        
        Args:
            transcript_id: UUID of the transcript
        
        Returns:
            Dictionary with speech metrics or None if not found
        """
        try:
            query = """
            SELECT 
                metrics_id,
                transcript_id,
                filler_word_count,
                total_word_count,
                filler_word_percentage,
                fluency_score,
                speech_rate,
                articulation_rate,
                total_pause_time,
                pause_count,
                pause_durations,
                articulation_score,
                created_at
            FROM speech_metrics
            WHERE transcript_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            result = execute_query(query, (transcript_id,), fetch_one=True)
            
            if result:
                # Parse pause_durations JSONB
                pause_durations = result['pause_durations']
                if isinstance(pause_durations, str):
                    pause_durations = json.loads(pause_durations)
                elif pause_durations is None:
                    pause_durations = {}
                
                return {
                    'metrics_id': result['metrics_id'],
                    'transcript_id': result['transcript_id'],
                    'filler_word_count': result['filler_word_count'],
                    'total_word_count': result['total_word_count'],
                    'filler_word_percentage': result['filler_word_percentage'],
                    'fluency_score': result['fluency_score'],
                    'speech_rate': result['speech_rate'],
                    'articulation_rate': result['articulation_rate'],
                    'total_pause_time': result['total_pause_time'],
                    'pause_count': result['pause_count'],
                    'pause_durations': pause_durations,
                    'articulation_score': result['articulation_score'],
                    'created_at': result['created_at']
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Failed to retrieve speech metrics: {e}")
            return None


# Global service instance
speech_metrics_service = SpeechMetricsService()
