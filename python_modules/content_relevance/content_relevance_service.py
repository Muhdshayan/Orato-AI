"""
Content Relevance – Service
=============================
Main service class.  Orchestrates scoring and persists results.

Follows the host-project singleton pattern
(cf. ``python_modules/nlp_asr/speech_metrics_service.py``).

Thread-safe and synchronous — designed to run inside
``asyncio.to_thread(...)`` in the analysis orchestrator.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from app.core.database import execute_query

from python_modules.content_relevance.scorer import score
from python_modules.content_relevance.models import ContentRelevanceResult

logger = logging.getLogger("content_relevance.service")


class ContentRelevanceService:
    """Analyse transcript content relevance and persist the result."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_and_store(
        self,
        transcript_id: str,
        full_text: str,
        declared_topic: str,
    ) -> dict:
        """
        Run the full content-relevance pipeline and INSERT into the
        ``content_relevance`` table.

        Parameters
        ----------
        transcript_id : str
            UUID of the transcript row (FK to ``transcripts``).
        full_text : str
            Raw transcript text.
        declared_topic : str
            Topic the speaker claimed to be discussing.

        Returns
        -------
        dict
            The API-ready result dictionary.
        """
        logger.info(
            "Starting content-relevance analysis for transcript %s (topic=%r)",
            transcript_id,
            declared_topic,
        )

        # 1. Pure scoring — no DB contact
        result: ContentRelevanceResult = score(full_text, declared_topic)

        # 2. Persist
        api_dict = result.to_api_dict()
        self._store(transcript_id, api_dict)

        logger.info(
            "Content-relevance analysis complete for transcript %s  "
            "(topic_match=%.2f, factual=%.2f, overall=%d)",
            transcript_id,
            api_dict["topic_match_score"],
            api_dict["factual_accuracy"],
            api_dict["overall_content_score"],
        )
        return api_dict

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def _store(transcript_id: str, data: dict) -> None:
        """INSERT one row into ``content_relevance``."""
        try:
            claim_results = data.get("claim_results", [])
            evidence_payload = {
                "snippets": data.get("evidence_snippets", []),
                "claim_results": claim_results,
            }
            logger.info(f"Storing content relevance: transcript_id={transcript_id}, topic_match={data['topic_match_score']}, factual={data['factual_accuracy']}")
            execute_query(
                """
                INSERT INTO content_relevance
                    (transcript_id, topic_match_score, off_topic_segments,
                     factual_accuracy, evidence_snippets)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    transcript_id,
                    data["topic_match_score"],
                    json.dumps(data["off_topic_segments"]),
                    data["factual_accuracy"],
                    json.dumps(evidence_payload),
                ),
            )
            logger.info(f"✅ Successfully stored content relevance for transcript_id={transcript_id}")
        except Exception as e:
            logger.error(f"❌ Failed to store content relevance for transcript_id={transcript_id}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise

    # ------------------------------------------------------------------
    # Read helper (used by the API endpoint)
    # ------------------------------------------------------------------

    @staticmethod
    def get_by_transcript(transcript_id: str) -> Dict[str, Any] | None:
        """Fetch the stored result for a transcript, or ``None``."""
        rows = execute_query(
            """
            SELECT topic_match_score, off_topic_segments,
                   factual_accuracy, evidence_snippets
            FROM content_relevance
            WHERE transcript_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (transcript_id,),
        )
        if not rows:
            return None

        row = rows[0]
        
        # Handle both tuple and dict returns from execute_query
        if isinstance(row, (list, tuple)):
            topic_score = float(row[0])
            off_topic = row[1] if isinstance(row[1], list) else json.loads(row[1] or "[]")
            factual = float(row[2])
            snippets_raw = row[3] if isinstance(row[3], (list, dict)) else json.loads(row[3] or "[]")
        else:
            # Dict return (RealDictCursor)
            topic_score = float(row.get("topic_match_score", 0))
            off_topic_raw = row.get("off_topic_segments", "[]")
            off_topic = off_topic_raw if isinstance(off_topic_raw, list) else json.loads(off_topic_raw or "[]")
            factual = float(row.get("factual_accuracy", 0))
            snippets_db_raw = row.get("evidence_snippets", "[]")
            snippets_raw = snippets_db_raw if isinstance(snippets_db_raw, (list, dict)) else json.loads(snippets_db_raw or "[]")

        if isinstance(snippets_raw, dict):
            snippets = snippets_raw.get("snippets", [])
            claim_results = snippets_raw.get("claim_results", [])
        elif isinstance(snippets_raw, list):
            # Backward compatibility with older rows that stored snippets as a plain array.
            snippets = snippets_raw
            claim_results = []
        else:
            snippets = []
            claim_results = []

        extracted_claims = [
            c.get("claim", "")
            for c in claim_results
            if isinstance(c, dict) and c.get("claim")
        ]

        # Derive computed fields expected by the frontend
        if topic_score >= 0.70:
            label = "High"
        elif topic_score >= 0.40:
            label = "Medium"
        else:
            label = "Low"

        overall = max(0, min(100, int(round(topic_score * 40 + factual * 60) * 100 / 100)))

        return {
            "topic_match_score": round(topic_score, 4),
            "topic_match_label": label,
            "off_topic_segments": off_topic,
            "factual_accuracy": round(factual, 4),
            "evidence_snippets": snippets,
            "claim_results": claim_results,
            "extracted_claims": extracted_claims,
            "overall_content_score": overall,
        }


# Module-level singleton (matches host-project convention)
content_relevance_service = ContentRelevanceService()
