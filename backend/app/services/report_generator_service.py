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

class ModularFeedbackModel(BaseModel):
    insights: List[str] = Field(description="A list of 3-4 natural, professional coaching insights based on the provided metrics")

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
            # Bug 2 Fix: Use raw eye contact percentage, not the 0-100 score
            "eye_contact": round(visual.get("head_pose", {}).get("eye_contact_percentage", 0), 1) if visual else "N/A",
            "gpm": round(visual.get("gestures", {}).get("gesture_frequency", {}).get("gestures_per_minute", 0), 1) if visual else "N/A",
            # Bug 6 Fix: Use raw CCA angle in degrees, not the 0-100 score
            "cca": round(visual.get("posture", {}).get("craniocervical_angle", {}).get("mean", 0), 1) if visual else "N/A",
            "hand_vis": round(visual.get("gestures", {}).get("hand_visibility", {}).get("any_hand_percentage", 0), 1) if visual else "N/A",
            "content_score": round(content.get("overall_score", 0), 1) if content else "N/A",
            "format_instructions": format_instructions
        }

        try:
            chain = prompt_template | self.llm | self.output_parser
            response = await chain.ainvoke(inputs)
            return response
        except Exception as e:
            logger.error(f"❌ LLM Report Generation Failed: {e}. Using rule-based fallback.")
            return self._get_rule_based_fallback(speech, visual, content, final_score)

    def _get_rule_based_fallback(self, speech: dict, visual: dict, content: dict, final_score: float) -> dict:
        """Provides a simplified, threshold-based report when LLM is unavailable."""
        praise = "You completed your session successfully."
        weakness = "General performance is stable, but can be more dynamic."
        plan = ["Practice your delivery for more consistency."]
        
        # Speech Heuristics
        if speech:
            rate = speech.get("speech_rate", 0)
            fillers = speech.get("filler_word_percentage", 0)
            if 115 <= rate <= 145: praise = "Your vocal pacing is steady and professional."
            elif rate < 110: weakness = "Your delivery is slightly too slow, which may impact audience engagement."
            elif rate > 155: weakness = "You are speaking quite fast; try adding meaningful pauses."
            
            if fillers > 4.1: plan.append("Try to replace filler words (ums/ahs) with silent pauses.")

        # Visual Heuristics
        if visual:
            scores = visual.get("individual_scores", {})
            eye = scores.get("eye_contact_score", 0)
            hand = scores.get("hand_visibility_score", 0)
            if 50 <= eye <= 70: praise = "You maintained excellent, non-intimidating eye contact."
            elif eye < 40: weakness = "Increase your eye contact to build better trust with the audience."
            if hand < 80: plan.append("Keep your hands visible to project transparency and confidence.")

        return {
            "praise": praise,
            "biggest_weakness": weakness,
            "action_plan": plan,
            "overall_score": round(final_score, 1),
            "is_fallback": True
        }

    async def generate_visual_insights(self, submission_id: str) -> List[str]:
        """Generates 3-4 professional coaching insights for visual performance."""
        # Check database first to prevent redundant LLM generation
        query = "SELECT visual_insights_json FROM analysis_reports WHERE submission_id = %s"
        record = execute_query(query, (submission_id,), fetch_one=True)
        if record and record.get('visual_insights_json'):
            data = record['visual_insights_json']
            return json.loads(data) if isinstance(data, str) else data

        visual = await self._get_visual_metrics(submission_id)
        if not visual: return ["Visual data is still being processed."]

        scores = visual.get("individual_scores", {})
        gestures = visual.get("gestures", {})
        
        prompt = ChatPromptTemplate.from_template(
            """You are a professional body language and kinesics coach. 
            Analyze these visual metrics and provide 3-4 concise, professional, and natural-sounding coaching insights.
            
            METRICS:
            - Eye Contact Score: {eye_contact}% (Target: 50-70% Connection Zone)
            - Hand Visibility: {hand_vis}% (Target: >80% for trust)
            - Posture Mastery: {posture}% (Target: >70% for authority)
            - Gesture Frequency: {gpm} GPM (Target: 10-16 GPM for energy)
            - Motion Burstiness: {burst} (Higher is more 'fidgety' or 'sudden')

            REQUIREMENTS:
            - Output ONLY a JSON list of 3-4 strings under the key 'insights'.
            - NO raw decimals. Use rounded values (e.g. 78%).
            - Tone: Constructive, authoritative, and human.
            - Focus on the 'why' and how it affects the audience.
            """
        )
        
        parser = JsonOutputParser(pydantic_object=ModularFeedbackModel)
        inputs = {
            "eye_contact": round(scores.get("eye_contact_score", 0), 0),
            "hand_vis": round(scores.get("hand_visibility_score", 0), 0),
            "posture": round(scores.get("cca_score", 0), 0),
            "gpm": round(gestures.get("gesture_frequency", {}).get("gestures_per_minute", 0), 1),
            "burst": round(visual.get("motion_energy", {}).get("burstiness_metrics", {}).get("burstiness", 0), 2)
        }
        
        try:
            # Use raw LLM string output to avoid strict Pydantic parser failures
            # when the LLM adds pre-amble text like "Here are the insights:"
            from langchain_core.output_parsers import StrOutputParser
            chain = prompt | self.llm | StrOutputParser()
            raw = await chain.ainvoke(inputs)
            
            # Try strict JSON parse first, then fall back to regex extraction
            insights = None
            try:
                parsed = json.loads(raw)
                insights = parsed.get("insights", [])
            except json.JSONDecodeError:
                import re
                match = re.search(r'"insights"\s*:\s*(\[.*?\])', raw, re.DOTALL)
                if match:
                    insights = json.loads(match.group(1))
            
            if not insights or not isinstance(insights, list):
                insights = ["Keep maintaining your professional presence."]
            
            # Persist insights into the database
            store_query = """
                INSERT INTO analysis_reports (submission_id, visual_insights_json)
                VALUES (%s, %s)
                ON CONFLICT (submission_id) DO UPDATE 
                SET visual_insights_json = EXCLUDED.visual_insights_json
            """
            execute_query(store_query, (submission_id, json.dumps(insights)))
            return insights
        except Exception as e:
            logger.error(f"Visual Insights Failed: {e}")
            return ["Hold steady posture to project authority.", "Maintain consistent hand visibility."]

    async def generate_delivery_insights(self, submission_id: str) -> List[str]:
        """Generates 3-4 professional coaching insights for speech delivery."""
        # Check database first to prevent redundant LLM generation
        query = "SELECT delivery_insights_json FROM analysis_reports WHERE submission_id = %s"
        record = execute_query(query, (submission_id,), fetch_one=True)
        if record and record.get('delivery_insights_json'):
            data = record['delivery_insights_json']
            return json.loads(data) if isinstance(data, str) else data

        speech = await self._get_speech_metrics(submission_id)
        if not speech: return ["Speech metrics are still being analyzed."]

        prompt = ChatPromptTemplate.from_template(
            """You are a world-class speech and vocal delivery coach. 
            Analyze these delivery metrics and provide 3-4 concise, professional, and natural-sounding coaching insights.
            
            METRICS:
            - Speaking Rate: {wpm} WPM (Target: 110-150 WPM)
            - Filler Content: {filler}% (Target: <4.1% for fluency)
            - Fluency Mastery: {fluency}/100
            - Pause Strategy: {pause_pct}% time spent in silence
            - Articulation Depth: {art}/100

            REQUIREMENTS:
            - Output ONLY a JSON list of 3-4 strings under the key 'insights'.
            - NO raw decimals. Use rounded values (e.g. 135 WPM).
            - Tone: Academic, encouraging, and narrative.
            - Focus on the audience's ability to retain information.
            """
        )
        
        parser = JsonOutputParser(pydantic_object=ModularFeedbackModel)
        inputs = {
            "wpm": round(speech.get("speech_rate", 0), 0),
            "filler": round(speech.get("filler_word_percentage", 0), 1),
            "fluency": round(speech.get("fluency_score", 0), 0),
            "pause_pct": round(speech.get("pause_percentage", 0), 1),
            "art": max(0, round(100 - abs(speech.get("articulation_rate", 150) - 150) * 0.8, 0)) # Fixed 0-100 mathematical clamp
        }
        
        try:
            chain = prompt | self.llm | parser
            res = await chain.ainvoke(inputs)
            insights = res.get("insights", ["Maintain your current vocal rhythm."])
            
            # Persist insights into the database
            store_query = """
                INSERT INTO analysis_reports (submission_id, delivery_insights_json)
                VALUES (%s, %s)
                ON CONFLICT (submission_id) DO UPDATE 
                SET delivery_insights_json = EXCLUDED.delivery_insights_json
            """
            execute_query(store_query, (submission_id, json.dumps(insights)))
            return insights
        except Exception as e:
            logger.error(f"Delivery Insights Failed: {e}")
            return ["Speak with clear intention and measured pacing.", "Minimize fillers to maximize clarity."]

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
