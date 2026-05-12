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

    def _as_number(self, value, default: float = 0.0) -> float:
        """Safely coerce DB/JSON values to float."""
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _metric_for_prompt(self, value, decimals: int = 1):
        """Return rounded numeric metric for prompt, or 'N/A' when unavailable."""
        if value is None:
            return "N/A"
        try:
            return round(float(value), decimals)
        except (TypeError, ValueError):
            return "N/A"

    def _normalize_feedback(self, feedback: Any) -> dict:
        """Convert parser output into a plain JSON-serializable dict."""
        if feedback is None:
            return {}

        if isinstance(feedback, dict):
            return feedback

        if hasattr(feedback, "model_dump"):
            return feedback.model_dump()

        if hasattr(feedback, "dict"):
            return feedback.dict()

        try:
            return dict(feedback)
        except Exception:
            return {"raw": str(feedback)}

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
        feedback = self._normalize_feedback(feedback)

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
        s_score = self._as_number(speech.get("fluency_score") if speech else None, 50.0)
        v_score = self._as_number(visual.get("overall_score") if visual else None, 50.0)
        c_score = self._as_number(content.get("overall_score") if content else None, 0.0)
        
        # Scale content score to 0-100 if it isn't (assuming it might be 0-1 from some modules)
        if 0 < c_score <= 1.0:
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
        
        try:
            # Prepare inputs with null-safe rounding for cleaner internal analysis
            content_score = self._as_number(content.get("overall_score") if content else None, 0.0)
            if 0 < content_score <= 1.0:
                content_score *= 100

            inputs = {
                "final_score": self._metric_for_prompt(final_score, 1),
                "wpm": self._metric_for_prompt(speech.get("speech_rate") if speech else None, 1),
                "filler_pct": self._metric_for_prompt(speech.get("filler_word_percentage") if speech else None, 2),
                "eye_contact": self._metric_for_prompt((visual or {}).get("individual_scores", {}).get("eye_contact_score"), 1),
                "gpm": self._metric_for_prompt((visual or {}).get("gestures", {}).get("gesture_frequency", {}).get("gestures_per_minute"), 1),
                "cca": self._metric_for_prompt((visual or {}).get("individual_scores", {}).get("cca_score"), 1),
                "hand_vis": self._metric_for_prompt((visual or {}).get("individual_scores", {}).get("hand_visibility_score"), 1),
                "content_score": self._metric_for_prompt(content_score, 1),
                "format_instructions": format_instructions
            }

            chain = prompt_template | self.llm | self.output_parser
            response = await chain.ainvoke(inputs)
            return response
        except Exception as e:
            logger.error(f"❌ LLM Report Generation Failed: {e}")
            return {
                "praise": "You completed your session successfully.",
                "biggest_weakness": "Analysis error.",
                "detailed_analysis": {
                    "speech": "Speech analytics could not be fully generated in this pass.",
                    "visual": "Visual analytics could not be fully generated in this pass.",
                    "content": "Content relevance analytics could not be fully generated in this pass."
                },
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
        tips_payload = self._normalize_feedback(tips)
        query = """
            INSERT INTO analysis_reports (report_id, submission_id, overall_score, tips_json)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (submission_id) DO UPDATE 
            SET overall_score = EXCLUDED.overall_score, tips_json = EXCLUDED.tips_json
        """
        execute_query(query, (report_id, submission_id, score, json.dumps(tips_payload)))
        return report_id

# Instantiate global service
report_generator_service = ReportGeneratorService()
