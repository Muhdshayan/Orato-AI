"""
Pause Detection Service
Analyzes speech segments to detect pauses between speech segments
"""
from typing import Dict, List, Any, Optional

class PauseDetectionService:
    """Service for detecting pauses and calculating speech/articulation rates"""
    
    # Threshold for what counts as a pause (in seconds)
    PAUSE_THRESHOLD = 0.2  # 200ms - standard in speech analysis
    
    # Classification thresholds for pause types
    SHORT_PAUSE_MAX = 0.5    # < 0.5s = short pause
    MEDIUM_PAUSE_MAX = 1.0   # 0.5-1.0s = medium pause (research-backed)
    EXTREME_PAUSE_MIN = 2.0  # >= 2.0s = extreme pause (rare in fluent adults)
    # > 1.0s = long pause; >= 2.0s = extreme pause
    
    def __init__(self):
        """Initialize the pause detection service"""
        pass
    
    def detect_pauses(
        self, 
        segment_timestamps: List[Dict[str, Any]], 
        audio_duration: float
    ) -> Dict[str, Any]:
        """
        Detect pauses between speech segments
        
        Args:
            segment_timestamps: List of segments with 'start', 'end', 'text'
            audio_duration: Total audio duration in seconds
        
        Returns:
            Dictionary with pause analysis:
                - pauses: List of detected pauses with timestamps
                - summary: Statistics about pauses (includes net_speaking_time)
        """
        if not segment_timestamps or len(segment_timestamps) < 2:
            # Need at least 2 segments to detect pauses
            return self._empty_result(audio_duration)
        
        # Step 1: Calculate all gaps between segments
        gaps = self._calculate_gaps(segment_timestamps)
        
        # Step 2: Filter for actual pauses (>= threshold)
        pauses = self._filter_pauses(gaps)
        
        # Step 3: Classify pause types
        pauses = self._classify_pauses(pauses)
        
        # Step 4: Calculate summary statistics
        summary = self._calculate_statistics(pauses, audio_duration)
        
        return {
            'pauses': pauses,
            'summary': summary
        }
    
    def _calculate_gaps(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate gaps between consecutive segments"""
        gaps = []
        
        for i in range(len(segments) - 1):
            current_end = segments[i]['end']
            next_start = segments[i + 1]['start']
            
            gap_duration = next_start - current_end
            
            # Only include if gap is positive (no overlap)
            if gap_duration > 0:
                gap = {
                    'start': current_end,
                    'end': next_start,
                    'duration': round(gap_duration, 3),
                    'after_segment': i,
                    'before_segment': i + 1
                }
                gaps.append(gap)
        
        return gaps
    
    def _filter_pauses(self, gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter gaps to only include those above the pause threshold"""
        pauses = [
            gap for gap in gaps 
            if gap['duration'] >= self.PAUSE_THRESHOLD
        ]
        return pauses
    
    def _classify_pauses(self, pauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classify pauses as short, medium, or long"""
        for pause in pauses:
            duration = pause['duration']
            
            if duration < self.SHORT_PAUSE_MAX:
                pause['type'] = 'short'
            elif duration < self.MEDIUM_PAUSE_MAX:
                pause['type'] = 'medium'
            elif duration < self.EXTREME_PAUSE_MIN:
                pause['type'] = 'long'
            else:
                pause['type'] = 'extreme'
        
        return pauses
    
    def _calculate_statistics(
        self, 
        pauses: List[Dict[str, Any]], 
        audio_duration: float
    ) -> Dict[str, Any]:
        """Calculate summary statistics for pauses"""
        
        if not pauses:
            return {
                'total_pause_time': 0.0,
                'pause_count': 0,
                'average_pause_duration': 0.0,
                'longest_pause': 0.0,
                'shortest_pause': 0.0,
                'net_speaking_time': audio_duration,
                'pause_percentage': 0.0
            }
        
        # Calculate totals
        total_pause_time = sum([p['duration'] for p in pauses])
        pause_count = len(pauses)
        
        # Calculate net speaking time
        net_speaking_time = audio_duration - total_pause_time
        
        # Calculate statistics
        average_pause = total_pause_time / pause_count
        longest_pause = max([p['duration'] for p in pauses])
        shortest_pause = min([p['duration'] for p in pauses])
        pause_percentage = (total_pause_time / audio_duration * 100) if audio_duration > 0 else 0
        
        # Count pause types
        short_pauses = sum(1 for p in pauses if p['type'] == 'short')
        medium_pauses = sum(1 for p in pauses if p['type'] == 'medium')
        long_pauses = sum(1 for p in pauses if p['type'] == 'long')
        extreme_pauses = sum(1 for p in pauses if p['type'] == 'extreme')
        
        return {
            'total_pause_time': round(total_pause_time, 2),
            'pause_count': pause_count,
            'average_pause_duration': round(average_pause, 3),
            'longest_pause': round(longest_pause, 3),
            'shortest_pause': round(shortest_pause, 3),
            'net_speaking_time': round(net_speaking_time, 2),
            'pause_percentage': round(pause_percentage, 2),
            'short_pause_count': short_pauses,
            'medium_pause_count': medium_pauses,
            'long_pause_count': long_pauses,
            'extreme_pause_count': extreme_pauses
        }
    
    def _empty_result(self, audio_duration: float) -> Dict[str, Any]:
        """Return empty result when no pauses can be detected"""
        return {
            'pauses': [],
            'summary': {
                'total_pause_time': 0.0,
                'pause_count': 0,
                'average_pause_duration': 0.0,
                'longest_pause': 0.0,
                'shortest_pause': 0.0,
                'net_speaking_time': audio_duration,
                'pause_percentage': 0.0,
                'short_pause_count': 0,
                'medium_pause_count': 0,
                'long_pause_count': 0
            }
        }
    
    def get_pause_insights(self, pause_data: Dict[str, Any]) -> str:
        """
        Generate human-readable insights from pause analysis
        
        Args:
            pause_data: Result from detect_pauses()
        
        Returns:
            String with insights about pause patterns
        """
        summary = pause_data['summary']
        
        insights = []
        
        # Pause assessment
        pause_percentage = summary['pause_percentage']
        if pause_percentage > 20:
            insights.append(f"High pause time ({pause_percentage}%). Try to reduce long pauses.")
        elif pause_percentage > 10:
            insights.append(f"Moderate pause time ({pause_percentage}%).")
        else:
            insights.append("Good pause control.")
        
        # Pause count
        pause_count = summary['pause_count']
        if pause_count > 15:
            insights.append(f"Many pauses detected ({pause_count}). Work on maintaining flow.")
        elif pause_count > 0:
            insights.append(f"{pause_count} pause(s) detected.")
        
        # Long pauses
        long_pause_count = summary.get('long_pause_count', 0)
        if long_pause_count > 0:
            insights.append(f"{long_pause_count} long pause(s) detected. Work on smooth transitions.")
        
        extreme_pause_count = summary.get('extreme_pause_count', 0)
        if extreme_pause_count > 0:
            insights.append(f"{extreme_pause_count} extreme pause(s) (>2s) detected. This may indicate significant planning difficulty.")
        
        return " ".join(insights)


# Global service instance
pause_detection_service = PauseDetectionService()

