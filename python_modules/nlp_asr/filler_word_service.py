"""
Filler Word Detection Service
Analyzes transcripts contextually for filler words using Groq LLM to eliminate false positives.
"""
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.core.config import settings

class FillerOccurrence(BaseModel):
    word: str = Field(description="The exact filler word used (e.g. 'um', 'like', 'so')")
    weight: float = Field(description="The penalty weight: 1.0 (Acoustic), 0.7 (Crutches), 0.3 (Transitioners)")

class FillerAnalysisResult(BaseModel):
    fillers: List[FillerOccurrence] = Field(description="List of all detected true filler words.")

class FillerWordService:
    """Service for detecting and analyzing filler words in speech contextually via Groq API"""
    
    # Weights for different types of fillers (Provided to LLM merely for reference)
    FILLER_WEIGHTS = {
        'um': 1.0, 'uh': 1.0, 'er': 1.0, 'ah': 1.0, 'umm': 1.0, 'uhh': 1.0,
        'erm': 1.0, 'ehh': 1.0, 'ohh': 1.0, 'hmm': 0.8, 'mhm': 0.8,
        'like': 0.7, 'you know': 0.6, 'i mean': 0.5,
        'sort of': 0.4, 'kind of': 0.4,
        'basically': 0.3, 'actually': 0.3, 'literally': 0.3, 'so': 0.2,
        'well': 0.2, 'right': 0.2, 'okay': 0.2, 'ok': 0.2, 'yeah': 0.2
    }
    
    PROMPT_TEMPLATE = """You are an expert computational linguist. 
Read the following transcript and identify EVERY instance of a verbal filler.
Important Rules to avoid False Positives:
- DO NOT flag legitimate grammatical uses of words (e.g., "I like apples" is a verb, NOT a filler. "That is right" is an adjective, NOT a filler. "I did it so well" are Adverbs, NOT fillers).
- ONLY flag words used purely as conversational crutches, thinking noises, or filler transitions.

Filler Categories & Weights to assign:
1. Acoustic Fillers (Weight 1.0): um, uh, er, ah, uhh, umm, erm, ehh, ohh
2. Conversational Crutches (Weight 0.7): like, you know, i mean, hmm, mhm, sort of, kind of
3. Weak Transitioners (Weight 0.3): basically, actually, literally, so, well, right, okay, ok, yeah

Return an array of the TRUE fillers found with their corresponding weight. If none are found, return an empty array.

Transcript: "{transcript_text}"
{format_instructions}
"""
    
    def __init__(self):
        """Initialize the pure LLM filler word service"""
        self.parser = JsonOutputParser(pydantic_object=FillerAnalysisResult)
        self.prompt = ChatPromptTemplate.from_template(self.PROMPT_TEMPLATE)

    def detect_fillers(self, transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send transcript to Groq LLM for contextual filler word extraction
        """
        full_text = transcript_data.get('full_text', '')
        audio_duration = transcript_data.get('audio_duration', 0)
        total_words = len(full_text.split())

        if total_words == 0:
            return self._empty_result(audio_duration)

        llm = ChatGroq(
            temperature=0.0,
            model_name="llama-3.3-70b-versatile",
            groq_api_key=settings.GROQ_API_KEY
        )
        
        chain = self.prompt | llm | self.parser
        
        try:
            print("🤖 Calling Groq LLM for contextual filler word detection...")
            result = chain.invoke({
                "transcript_text": full_text,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            fillers = result.get('fillers', [])
            
            filler_count = len(fillers)
            weighted_count = sum(f.get('weight', 1.0) for f in fillers)
            filler_percentage = (filler_count / total_words * 100) if total_words > 0 else 0
            
            fluency_score = self._calculate_fluency_score(
                filler_count, weighted_count, total_words, audio_duration
            )
            
            filler_details = [{"word": f.get("word"), "weight": f.get("weight")} for f in fillers]
            
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
            
        except Exception as e:
            print(f"⚠️ LLM Filler Detection Failed. Error: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_result(audio_duration)

    def _empty_result(self, audio_duration: float) -> Dict[str, Any]:
        """Fallback for failed analysis"""
        return {
            'filler_word_count': 0,
            'total_words': 0,
            'filler_percentage': 0.0,
            'filler_details': [],
            'fluency_score': 100.0,
            'weighted_filler_count': 0.0,
            'audio_duration': audio_duration,
            'words_per_minute': 0.0
        }

    def _calculate_fluency_score(
        self, 
        filler_count: int, 
        weighted_count: float, 
        total_words: int, 
        audio_duration: float
    ) -> float:
        """Calculate score exactly as before based on Groq's verified weights"""
        if total_words == 0:
            return 100.0
            
        weighted_percentage = (weighted_count / total_words) * 100
        
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
            
        if audio_duration > 0:
            fillers_per_minute = (filler_count / audio_duration) * 60
            if fillers_per_minute > 10:
                density_penalty = min((fillers_per_minute - 10) * 2, 20)
                score = max(0, score - density_penalty)
                
        return max(0, min(100, score))

    def get_filler_summary(self, analysis_result: Dict[str, Any]) -> str:
        """Same summary function as before!"""
        filler_count = analysis_result['filler_word_count']
        total_words = analysis_result['total_words']
        filler_percentage = analysis_result['filler_percentage']
        fluency_score = analysis_result['fluency_score']
        
        if fluency_score >= 90: rating = "Excellent"
        elif fluency_score >= 75: rating = "Good"
        elif fluency_score >= 60: rating = "Fair"
        elif fluency_score >= 40: rating = "Poor"
        else: rating = "Needs Improvement"
        
        summary = f"Filler Word Analysis Summary:\n-----------------------------\nTotal Words: {total_words}\nFiller Words: {filler_count}\nFiller Percentage: {filler_percentage}%\nFluency Score: {fluency_score}/100 ({rating})\n\nThe speaker used {filler_count} filler words out of {total_words} total words ({filler_percentage}%).\n"
        
        if fluency_score >= 75: summary += "This indicates good speech fluency with minimal filler word usage."
        elif fluency_score >= 60: summary += "There is room for improvement in reducing filler word usage."
        else: summary += "Consider practicing to reduce filler words for better speech clarity."
        
        return summary.strip()

# Global service instance
filler_word_service = FillerWordService()
