import asyncio
import json
import logging
import uuid
from typing import Dict, Any, List
from app.core.database import execute_query
from app.core.config import settings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class FeedbackModel(BaseModel):
    praise: str = Field(description="Narrative praise highlighting specific successful moments or patterns")
    biggest_weakness: str = Field(description="A professional, tactful but honest evaluation of the single biggest growth area")
    detailed_analysis: Dict[str, str] = Field(description="In-depth analysis for 'Speech', 'Visual', and 'Content' categories")
    action_plan: List[str] = Field(description="3-5 highly specific, actionable steps for the next presentation")

class ReportGeneratorService:
    """
    Service to aggregate modular analysis data into a cumulative report 
    with AI-driven insights based on research-backed thresholds.
    """

    def __init__(self):
        # Research-backed thresholds for scoring
        self.RESEARCH_THRESHOLDS = {
            "wpm": {"min": 110, "max": 150},
            "filler_density": 4.1,  # Detrimental if > 4.1%
            "long_pause": 1.0,      # Clinically significant boundary
            "eye_contact": {"min": 50, "max": 70}, # 50/70 rule
            "cca_angle": 40.0,      # Slouching threshold
            "gesture_frequency": {"min": 10, "max": 16}, # Medium Intensity Hypothesis
            "hand_visibility": 80.0 # Floor for trust projection
        }
        
        # Initialize Groq LLM
        self.llm = ChatGroq(
            temperature=0.3,
            model_name="llama-3.3-70b-versatile",
            groq_api_key=settings.GROQ_API_KEY
        )

        # Define modern JSON output parser
        self.output_parser = JsonOutputParser(pydantic_object=FeedbackModel)

    async def generate_report(self, submission_id: str) -> Dict[str, Any]:
        """
        Aggregates data, calculates score, and prompts LLM for custom report.
        """
        logger.info(f"📊 Generating cumulative report for {submission_id}")

        # 1. Fetch Modular Data
        speech_data = await self._get_speech_metrics(submission_id)
        visual_data = await self._get_visual_metrics(submission_id)
        content_data = await self._get_content_relevance(submission_id)

        # 2. Calculate Weighted Scores
        # Weights: Speech (35%), Visual (35%), Content (30%)
        cumulative_score = self._calculate_cumulative_score(speech_data, visual_data, content_data)

        # 3. Generate LLM Feedback
        feedback = await self._generate_ai_feedback(speech_data, visual_data, content_data, cumulative_score)

        # 4. Store in Database
        report_id = await self._store_report(submission_id, cumulative_score, feedback)

        return {
            "report_id": report_id,
            "overall_score": cumulative_score,
            "feedback": feedback,
            "status": "completed"
        }

    def _calculate_cumulative_score(self, speech: dict, visual: dict, content: dict) -> float:
        """Weighted aggregation logic."""
        s_score = speech.get("fluency_score", 50) if speech else 50
        v_score = visual.get("overall_score", 50) if visual else 50
        c_score = content.get("overall_score", 0) if content else 0
        
        # Scale content score to 0-100 if it isn't (assuming it might be 0-1 from some modules)
        if c_score <= 1.0 and c_score > 0:
            c_score *= 100

        weighted_score = (s_score * 0.35) + (v_score * 0.35) + (c_score * 0.30)
        return round(weighted_score, 2)

    async def _generate_ai_feedback(self, speech: dict, visual: dict, content: dict, final_score: float) -> dict:
        """Constructs prompt using research constraints and calls Groq."""
        
        format_instructions = self.output_parser.get_format_instructions()
        
        prompt_template = ChatPromptTemplate.from_template(
            """You are a world-class executive communication coach and professional presentation judge (OratoAI). 
            Your goal is to provide a natural, conversational, and highly actionable performance assessment.

            CRITICAL DIRECTIVE: 
            - DO NOT use raw numeric values or long decimals in your narrative text (e.g., avoid "71.7622%").
            - Instead, use QUALITATIVE DESCRIPTIONS (e.g., "slightly elevated", "exceptionally steady", "distractingly frequent", "ideal rhythm").
            - Only mention a number if it is a rounded target (e.g., "Aim for under 5%") or a broad data point (e.g., "around 120 WPM").
            - Sound like a human judge speaking to a student, not a computer reporting data.

            CORE RESEARCH FOUNDATIONS (For your internal logic):
            - Fluency: Optimal Speech Rate is 110-150 WPM. Filler density >4.1% markers disfluency.
            - Visual Authority: 50-70% eye contact is the 'Connection Zone'. >70% is staring/aggressive.
            - Biomechanics: CCA < 40° signifies low presence/slouching. Hand visibility >80% projects trust.
            - Dynamics: 10-16 Gestures Per Minute projects confidence; higher is 'fidgety', lower is 'stiff'.

            SPEAKER METRICS (Analyze these, but describe them naturally):
            - Overall Metric Score: {final_score}/100
            - Vocal Pacing: {wpm} WPM
            - Disfluency (Filler) Rate: {filler_pct}%
            - Eye Contact Level: {eye_contact}%
            - Gesture Frequency: {gpm} GPM
            - Posture (CCA Angle): {cca}°
            - Hand Visibility Level: {hand_vis}%
            - Content Relevance Score: {content_score}/100

            REPORT REQUIREMENTS:
            1. TONALITY: Warm, authoritative, and narrative. 
            2. PRAISE: Highlight their most "natural" strengths.
            3. WEAKNESS: Describe the 'feeling' of the mistake (e.g., "The audience might feel stared at" rather than "Eye contact is 71%").
            4. DETAILED ANALYSIS: A professional two-sentence summary for 'Speech', 'Visual', and 'Content'.
            5. ACTION PLAN: 3 concrete, easy-to-understand 'Growth Steps'.

            {format_instructions}
            """
        )
        
        # Prepare inputs with rounded values for cleaner internal analysis
        inputs = {
            "final_score": round(final_score, 1),
            "wpm": round(speech.get("speech_rate", 0), 1) if speech else "N/A",
            "filler_pct": round(speech.get("filler_word_percentage", 0), 2) if speech else "N/A",
            "eye_contact": round(visual.get("individual_scores", {}).get("eye_contact_score", 0), 1) if visual else "N/A",
            "gpm": round(visual.get("gestures", {}).get("gesture_frequency", {}).get("gestures_per_minute", 0), 1) if visual else "N/A",
            "cca": round(visual.get("individual_scores", {}).get("cca_score", 0), 1) if visual else "N/A",
            "hand_vis": round(visual.get("individual_scores", {}).get("hand_visibility_score", 0), 1) if visual else "N/A",
            "content_score": round(content.get("overall_score", 0), 1) if content else "N/A",
            "format_instructions": format_instructions
        }

        try:
            chain = prompt_template | self.llm | self.output_parser
            response = await chain.ainvoke(inputs)
            return response
        except Exception as e:
            logger.error(f"❌ LLM Report Generation Failed: {e}")
            return {
                "praise": "You completed your session successfully.",
                "biggest_weakness": "Analysis error.",
                "action_plan": ["Review your raw metrics manually while we fix our AI coach."]
            }

    async def _get_speech_metrics(self, submission_id: str) -> dict:
        query = """
            SELECT sm.* 
            FROM speech_metrics sm
            JOIN transcripts t ON sm.transcript_id = t.transcript_id
            WHERE t.submission_id = %s
            ORDER BY sm.created_at DESC LIMIT 1
        """
        result = execute_query(query, (submission_id,), fetch_one=True)
        return result if result else {}

    async def _get_visual_metrics(self, submission_id: str) -> dict:
        query = """
            SELECT keypoints_json 
            FROM cv_artifacts 
            WHERE submission_id = %s AND frame_index = 0
            ORDER BY created_at DESC LIMIT 1
        """
        result = execute_query(query, (submission_id,), fetch_one=True)
        if result and result.get('keypoints_json'):
            data = result['keypoints_json']
            return json.loads(data) if isinstance(data, str) else data
        return {}

    async def _get_content_relevance(self, submission_id: str) -> dict:
        query = """
            SELECT cr.* 
            FROM content_relevance cr
            JOIN transcripts t ON cr.transcript_id = t.transcript_id
            WHERE t.submission_id = %s
            ORDER BY cr.created_at DESC LIMIT 1
        """
        result = execute_query(query, (submission_id,), fetch_one=True)
        if result:
            # Aggregate content score: average of topic match and factual accuracy
            scores = []
            if result.get('topic_match_score') is not None: scores.append(result['topic_match_score'])
            if result.get('factual_accuracy') is not None: scores.append(result['factual_accuracy'])
            
            result['overall_score'] = (sum(scores) / len(scores)) * 100 if scores else 0
            return result
        return {}

    async def _store_report(self, submission_id: str, score: float, tips: dict) -> str:
        # Use UUID for report_id
        import uuid
        report_id = str(uuid.uuid4())
        query = """
            INSERT INTO analysis_reports (report_id, submission_id, overall_score, tips_json)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (submission_id) DO UPDATE 
            SET overall_score = EXCLUDED.overall_score, tips_json = EXCLUDED.tips_json
        """
        execute_query(query, (report_id, submission_id, score, json.dumps(tips)))
        return report_id

# Instantiate global service
report_generator_service = ReportGeneratorService()
