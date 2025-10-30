"""
Speech Rate Service
Calculates speech rate and articulation rate metrics
"""
from typing import Dict, Any

class SpeechRateService:
    """Service for calculating speech and articulation rates"""
    
    # Standard speech rate ranges (words per minute)
    VERY_SLOW = 80
    SLOW = 100
    NORMAL_MIN = 110
    NORMAL_MAX = 150
    FAST = 160
    VERY_FAST = 180
    
    def __init__(self):
        """Initialize the speech rate service"""
        pass
    
    def calculate_rates(
        self,
        word_count: int,
        audio_duration: float,
        total_pause_time: float = 0
    ) -> Dict[str, Any]:
        """
        Calculate speech rate and articulation rate
        
        Args:
            word_count: Total number of words spoken
            audio_duration: Total audio duration in seconds
            total_pause_time: Total pause duration in seconds (default: 0)
        
        Returns:
            Dictionary with:
                - speech_rate: Words per minute (including pauses)
                - articulation_rate: Words per minute (excluding pauses)
                - net_speaking_time: Speaking time without pauses
                - speech_rate_category: Category (slow/normal/fast/etc.)
                - articulation_rate_category: Category for articulation rate
        """
        # Calculate speech rate (includes pauses)
        speech_rate = self.calculate_speech_rate(word_count, audio_duration)
        
        # Calculate net speaking time (exclude pauses)
        net_speaking_time = audio_duration - total_pause_time
        
        # Calculate articulation rate (excludes pauses)
        articulation_rate = self.calculate_articulation_rate(word_count, net_speaking_time)
        
        # Categorize rates
        speech_rate_category = self.categorize_rate(speech_rate)
        articulation_rate_category = self.categorize_rate(articulation_rate)
        
        return {
            'speech_rate': speech_rate,
            'articulation_rate': articulation_rate,
            'net_speaking_time': round(net_speaking_time, 2),
            'speech_rate_category': speech_rate_category,
            'articulation_rate_category': articulation_rate_category
        }
    
    def calculate_speech_rate(self, word_count: int, audio_duration: float) -> float:
        """
        Calculate speech rate (words per minute, including pauses)
        
        Speech Rate = Total Words / Total Duration (minutes)
        
        This is the overall speaking rate including all pauses and hesitations.
        Standard range: 110-150 WPM for presentations
        
        Args:
            word_count: Total number of words
            audio_duration: Total audio duration in seconds
        
        Returns:
            Speech rate in words per minute (WPM)
        """
        if audio_duration <= 0:
            return 0.0
        
        duration_minutes = audio_duration / 60
        speech_rate = word_count / duration_minutes
        
        return round(speech_rate, 2)
    
    def calculate_articulation_rate(self, word_count: int, net_speaking_time: float) -> float:
        """
        Calculate articulation rate (words per minute, excluding pauses)
        
        Articulation Rate = Total Words / Net Speaking Time (minutes)
        
        This measures actual speaking speed without pauses.
        Typically 10-20% higher than speech rate.
        
        Args:
            word_count: Total number of words
            net_speaking_time: Speaking time without pauses in seconds
        
        Returns:
            Articulation rate in words per minute (WPM)
        """
        if net_speaking_time <= 0:
            return 0.0
        
        speaking_minutes = net_speaking_time / 60
        articulation_rate = word_count / speaking_minutes
        
        return round(articulation_rate, 2)
    
    def categorize_rate(self, rate: float) -> str:
        """
        Categorize speech/articulation rate
        
        Args:
            rate: Rate in words per minute
        
        Returns:
            Category string: 'very_slow', 'slow', 'normal', 'fast', 'very_fast'
        """
        if rate < self.VERY_SLOW:
            return 'very_slow'
        elif rate < self.SLOW:
            return 'slow'
        elif rate < self.NORMAL_MIN:
            return 'slightly_slow'
        elif rate <= self.NORMAL_MAX:
            return 'normal'
        elif rate <= self.FAST:
            return 'fast'
        elif rate <= self.VERY_FAST:
            return 'very_fast'
        else:
            return 'extremely_fast'
    
    def get_rate_emoji(self, category: str) -> str:
        """
        Get emoji representation for rate category
        
        Args:
            category: Rate category
        
        Returns:
            Emoji string
        """
        emoji_map = {
            'very_slow': '🐌',
            'slow': '🐢',
            'slightly_slow': '🚶',
            'normal': '✅',
            'fast': '⚡',
            'very_fast': '🚀',
            'extremely_fast': '💨'
        }
        return emoji_map.get(category, '❓')
    
    def get_rate_label(self, category: str) -> str:
        """
        Get human-readable label for rate category
        
        Args:
            category: Rate category
        
        Returns:
            Label string
        """
        label_map = {
            'very_slow': 'Very Slow',
            'slow': 'Slow',
            'slightly_slow': 'Slightly Slow',
            'normal': 'Good Pace',
            'fast': 'Fast',
            'very_fast': 'Very Fast',
            'extremely_fast': 'Extremely Fast'
        }
        return label_map.get(category, 'Unknown')
    
    def get_rate_feedback(self, rate: float, rate_type: str = 'speech') -> str:
        """
        Get feedback/recommendation based on rate
        
        Args:
            rate: Rate in WPM
            rate_type: 'speech' or 'articulation'
        
        Returns:
            Feedback string
        """
        category = self.categorize_rate(rate)
        
        if rate_type == 'speech':
            feedback_map = {
                'very_slow': f"Your speech rate ({rate} WPM) is very slow. Try to speak faster to maintain audience engagement.",
                'slow': f"Your speech rate ({rate} WPM) is slow. Consider increasing your pace slightly.",
                'slightly_slow': f"Your speech rate ({rate} WPM) is slightly below normal. A bit faster would be ideal.",
                'normal': f"Excellent! Your speech rate ({rate} WPM) is in the ideal range for clear communication.",
                'fast': f"Your speech rate ({rate} WPM) is fast. Slow down slightly to ensure clarity.",
                'very_fast': f"Your speech rate ({rate} WPM) is very fast. Slow down significantly for better comprehension.",
                'extremely_fast': f"Your speech rate ({rate} WPM) is extremely fast. This may be difficult to understand."
            }
        else:  # articulation
            feedback_map = {
                'very_slow': f"Your articulation rate ({rate} WPM) is very slow when speaking.",
                'slow': f"Your articulation rate ({rate} WPM) is slow. You speak slowly when not pausing.",
                'slightly_slow': f"Your articulation rate ({rate} WPM) is slightly slow.",
                'normal': f"Good! Your articulation rate ({rate} WPM) shows natural speaking speed.",
                'fast': f"Your articulation rate ({rate} WPM) is fast when speaking continuously.",
                'very_fast': f"Your articulation rate ({rate} WPM) is very fast during actual speech.",
                'extremely_fast': f"Your articulation rate ({rate} WPM) is extremely fast when speaking."
            }
        
        return feedback_map.get(category, f"Rate: {rate} WPM")
    
    def compare_rates(self, speech_rate: float, articulation_rate: float) -> Dict[str, Any]:
        """
        Compare speech rate and articulation rate to provide insights
        
        Args:
            speech_rate: Speech rate (with pauses)
            articulation_rate: Articulation rate (without pauses)
        
        Returns:
            Dictionary with comparison insights
        """
        difference = articulation_rate - speech_rate
        difference_percentage = (difference / speech_rate * 100) if speech_rate > 0 else 0
        
        # Interpret the difference
        if difference_percentage < 5:
            interpretation = "Very few pauses. You speak with minimal breaks."
        elif difference_percentage < 15:
            interpretation = "Good balance between speaking and pausing."
        elif difference_percentage < 25:
            interpretation = "Moderate pauses. Consider reducing long breaks."
        else:
            interpretation = "Significant pauses detected. Work on maintaining flow."
        
        return {
            'difference': round(difference, 2),
            'difference_percentage': round(difference_percentage, 2),
            'interpretation': interpretation
        }


# Global service instance
speech_rate_service = SpeechRateService()

