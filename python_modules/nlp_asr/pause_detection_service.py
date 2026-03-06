"""
Pause Detection Service
Analyzes speech segments to detect pauses between speech segments
"""
from typing import Dict, List, Any, Optional

class PauseDetectionService:
    """Service for detecting pauses and calculating speech/articulation rates"""
    
    # Threshold for what counts as a pause (in seconds)
    # Lowered to 0.1s to catch "micro-pauses" visible in the graph
    PAUSE_THRESHOLD = 0.1  
    
    # Classification thresholds for pause types
    SHORT_PAUSE_MAX = 0.5    # < 0.5s = short pause
    MEDIUM_PAUSE_MAX = 1.0   # 0.5-1.0s = medium pause (research-backed)
    EXTREME_PAUSE_MIN = 2.0  # >= 2.0s = extreme pause (rare in fluent adults)
    
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
        """
        if not segment_timestamps or len(segment_timestamps) < 2:
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
            # Normalize keys (some parsers use tuple, some dict)
            curr = segments[i]
            next_seg = segments[i + 1]
            
            # Handle dictionary vs list format
            if isinstance(curr, dict):
                current_end = float(curr.get('end', 0))
            elif isinstance(curr, (list, tuple)):
                current_end = float(curr[1])
            else: continue

            if isinstance(next_seg, dict):
                next_start = float(next_seg.get('start', 0))
            elif isinstance(next_seg, (list, tuple)):
                next_start = float(next_seg[1])
            else: continue
            
            gap_duration = next_start - current_end
            
            # Use 3 decimal precision to avoid floating point issues (e.g. 0.199999)
            gap_duration = round(gap_duration, 3)

            # Only include if gap is positive (no overlap)
            if gap_duration > 0:
                gap = {
                    'start': current_end,
                    'end': next_start,
                    'duration': gap_duration,
                    'type': 'unknown', # Will be filled later
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
        
        # Guard clause for empty pauses
        if not pauses:
            return self._empty_stats(audio_duration)
        
        # Calculate totals
        total_pause_time = sum([p['duration'] for p in pauses])
        pause_count = len(pauses)
        
        # Safety clamp
        if total_pause_time > audio_duration:
            total_pause_time = audio_duration
        
        # Calculate net speaking time
        net_speaking_time = audio_duration - total_pause_time
        
        # Calculate statistics
        average_pause = total_pause_time / pause_count if pause_count > 0 else 0
        longest_pause = max([p['duration'] for p in pauses]) if pauses else 0
        shortest_pause = min([p['duration'] for p in pauses]) if pauses else 0
        
        # Percent calculation
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
            'summary': self._empty_stats(audio_duration)
        }

    def _empty_stats(self, audio_duration: float) -> Dict[str, Any]:
        return {
            'total_pause_time': 0.0,
            'pause_count': 0,
            'average_pause_duration': 0.0,
            'longest_pause': 0.0,
            'shortest_pause': 0.0,
            'net_speaking_time': audio_duration,
            'pause_percentage': 0.0,
            'short_pause_count': 0,
            'medium_pause_count': 0,
            'long_pause_count': 0,
            'extreme_pause_count': 0
        }
    
    def get_pause_insights(self, pause_data: Dict[str, Any]) -> str:
        """Generate human-readable insights from pause analysis"""
        summary = pause_data.get('summary', {})
        pause_percentage = summary.get('pause_percentage', 0)
        pause_count = summary.get('pause_count', 0)
        
        insights = []
        
        # Pause assessment
        if pause_percentage > 20:
            insights.append(f"High pause time ({pause_percentage}%). Try to maintain a steady flow.")
        elif pause_percentage > 10:
            insights.append(f"Moderate pause time ({pause_percentage}%). Good pacing.")
        elif pause_percentage > 2:
            insights.append("Good pause control.")
        else:
            insights.append("Very few pauses detected. Remember to breathe between sentences.")
        
        return " ".join(insights)

# Global service instance
pause_detection_service = PauseDetectionService()