"""
Filler Word Detection Service
Analyzes transcripts for filler words (um, uh, like, etc.) and calculates fluency scores
"""
from typing import Dict, List, Any
import re

class FillerWordService:
    """Service for detecting and analyzing filler words in speech"""
    
    # Common filler words in English
    FILLER_WORDS = {
        'um', 'uh', 'er', 'ah', 'like', 'you know', 'i mean', 
        'sort of', 'kind of', 'basically', 'actually', 'literally',
        'so', 'well', 'right', 'okay', 'ok', 'yeah', 'hmm', 'mhm',
        'erm', 'umm', 'uhh', 'ehh', 'ohh'
    }
    
    # Weights for different types of fillers (more distracting = higher weight)
    FILLER_WEIGHTS = {
        'um': 1.0,
        'uh': 1.0,
        'er': 1.0,
        'ah': 1.0,
        'umm': 1.0,
        'uhh': 1.0,
        'erm': 1.0,
        'ehh': 1.0,
        'ohh': 1.0,
        'hmm': 0.8,
        'mhm': 0.8,
        'like': 0.7,
        'you know': 0.6,
        'i mean': 0.5,
        'sort of': 0.4,
        'kind of': 0.4,
        'basically': 0.3,
        'actually': 0.3,
        'literally': 0.3,
        'so': 0.2,
        'well': 0.2,
        'right': 0.2,
        'okay': 0.2,
        'ok': 0.2,
        'yeah': 0.2
    }
    
    def __init__(self):
        """Initialize the filler word service"""
        pass
    
    def detect_fillers(self, transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect filler words in transcript and calculate metrics
        
        Args:
            transcript_data: Dictionary containing:
                - full_text: Complete transcript text
                - word_timestamps: List of word objects with timestamps (optional)
                - audio_duration: Duration of audio in seconds
        
        Returns:
            Dictionary with filler word analysis:
                - filler_word_count: Total count of filler words
                - total_words: Total word count
                - filler_percentage: Percentage of filler words
                - filler_details: List of detected fillers with positions
                - fluency_score: Score from 0-100 (higher is better)
                - weighted_filler_count: Weighted count considering severity
        """
        full_text = transcript_data.get('full_text', '')
        word_timestamps = transcript_data.get('word_timestamps', [])
        audio_duration = transcript_data.get('audio_duration', 0)
        
        # Analyze using word timestamps if available (more accurate)
        if word_timestamps:
            return self._analyze_with_timestamps(full_text, word_timestamps, audio_duration)
        else:
            return self._analyze_text_only(full_text, audio_duration)
    
    def _analyze_with_timestamps(
        self, 
        full_text: str, 
        word_timestamps: List[Dict], 
        audio_duration: float
    ) -> Dict[str, Any]:
        """Analyze filler words using word-level timestamps"""
        
        filler_details = []
        filler_count = 0
        weighted_count = 0.0
        total_words = len(word_timestamps)
        
        for idx, word_obj in enumerate(word_timestamps):
            word = word_obj.get('word', '').lower().strip()
            start_time = word_obj.get('start_offset', 0)
            end_time = word_obj.get('end_offset', 0)
            
            # Check for exact filler word match
            if word in self.FILLER_WORDS:
                weight = self.FILLER_WEIGHTS.get(word, 1.0)
                filler_count += 1
                weighted_count += weight
                
                filler_details.append({
                    'word': word,
                    'position': idx,
                    'start_time': start_time,
                    'end_time': end_time,
                    'weight': weight
                })
        
        # Calculate metrics
        filler_percentage = (filler_count / total_words * 100) if total_words > 0 else 0
        
        # Calculate fluency score (0-100, higher is better)
        fluency_score = self._calculate_fluency_score(
            filler_count, 
            weighted_count, 
            total_words, 
            audio_duration
        )
        
        return {
            'filler_word_count': filler_count,
            'total_words': total_words,
            'filler_percentage': round(filler_percentage, 2),
            'filler_details': filler_details,
            'fluency_score': round(fluency_score, 2),
            'weighted_filler_count': round(weighted_count, 2),
            'audio_duration': audio_duration,
            'words_per_minute': round((total_words / audio_duration * 60), 2) if audio_duration > 0 else 0
        }
    
    def _analyze_text_only(self, full_text: str, audio_duration: float) -> Dict[str, Any]:
        """Analyze filler words from text only (fallback method)"""
        
        # Convert to lowercase and split into words
        words = re.findall(r'\b\w+\b', full_text.lower())
        total_words = len(words)
        
        filler_details = []
        filler_count = 0
        weighted_count = 0.0
        
        for idx, word in enumerate(words):
            if word in self.FILLER_WORDS:
                weight = self.FILLER_WEIGHTS.get(word, 1.0)
                filler_count += 1
                weighted_count += weight
                
                filler_details.append({
                    'word': word,
                    'position': idx,
                    'weight': weight
                })
        
        # Calculate metrics
        filler_percentage = (filler_count / total_words * 100) if total_words > 0 else 0
        
        # Calculate fluency score
        fluency_score = self._calculate_fluency_score(
            filler_count, 
            weighted_count, 
            total_words, 
            audio_duration
        )
        
        return {
            'filler_word_count': filler_count,
            'total_words': total_words,
            'filler_percentage': round(filler_percentage, 2),
            'filler_details': filler_details,
            'fluency_score': round(fluency_score, 2),
            'weighted_filler_count': round(weighted_count, 2),
            'audio_duration': audio_duration,
            'words_per_minute': round((total_words / audio_duration * 60), 2) if audio_duration > 0 else 0
        }
    
    def _calculate_fluency_score(
        self, 
        filler_count: int, 
        weighted_count: float, 
        total_words: int, 
        audio_duration: float
    ) -> float:
        """
        Calculate fluency score based on filler word usage
        
        Score calculation:
        - Base score: 100
        - Penalty based on filler percentage (weighted)
        - Additional penalty for high filler density
        
        Returns:
            Float between 0-100 (higher is better)
        """
        if total_words == 0:
            return 100.0
        
        # Calculate filler percentage with weights
        weighted_percentage = (weighted_count / total_words) * 100
        
        # Base scoring system
        # Excellent: < 1% fillers -> 90-100
        # Good: 1-3% fillers -> 75-90
        # Fair: 3-5% fillers -> 60-75
        # Poor: 5-8% fillers -> 40-60
        # Very Poor: > 8% fillers -> 0-40
        
        if weighted_percentage < 1:
            score = 100 - (weighted_percentage * 10)
        elif weighted_percentage < 3:
            score = 90 - ((weighted_percentage - 1) * 7.5)
        elif weighted_percentage < 5:
            score = 75 - ((weighted_percentage - 3) * 7.5)
        elif weighted_percentage < 8:
            score = 60 - ((weighted_percentage - 5) * 6.67)
        else:
            score = max(0, 40 - ((weighted_percentage - 8) * 5))
        
        # Additional penalty for filler density (fillers per minute)
        if audio_duration > 0:
            fillers_per_minute = (filler_count / audio_duration) * 60
            if fillers_per_minute > 10:
                density_penalty = min((fillers_per_minute - 10) * 2, 20)
                score = max(0, score - density_penalty)
        
        return max(0, min(100, score))
    
    def get_filler_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of filler word analysis
        
        Args:
            analysis_result: Result from detect_fillers()
        
        Returns:
            String summary of the analysis
        """
        filler_count = analysis_result['filler_word_count']
        total_words = analysis_result['total_words']
        filler_percentage = analysis_result['filler_percentage']
        fluency_score = analysis_result['fluency_score']
        
        # Determine rating
        if fluency_score >= 90:
            rating = "Excellent"
        elif fluency_score >= 75:
            rating = "Good"
        elif fluency_score >= 60:
            rating = "Fair"
        elif fluency_score >= 40:
            rating = "Poor"
        else:
            rating = "Needs Improvement"
        
        summary = f"""
Filler Word Analysis Summary:
-----------------------------
Total Words: {total_words}
Filler Words: {filler_count}
Filler Percentage: {filler_percentage}%
Fluency Score: {fluency_score}/100 ({rating})

The speaker used {filler_count} filler words out of {total_words} total words ({filler_percentage}%).
"""
        
        if fluency_score >= 75:
            summary += "This indicates good speech fluency with minimal filler word usage."
        elif fluency_score >= 60:
            summary += "There is room for improvement in reducing filler word usage."
        else:
            summary += "Consider practicing to reduce filler words for better speech clarity."
        
        return summary.strip()


# Global service instance
filler_word_service = FillerWordService()

