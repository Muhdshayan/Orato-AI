"""
Content Relevance – Data Models
================================
Pure dataclasses / TypedDicts.  No DB or FastAPI imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OffTopicSegment:
    """A contiguous portion of the transcript that drifts from the declared topic."""
    text: str
    start: float          # approximate char-offset or timestamp start
    end: float            # approximate char-offset or timestamp end
    score: float          # relevance score for this segment (0-1, lower = less relevant)


@dataclass
class ClaimResult:
    """Verdict for a single atomic claim."""
    claim: str
    verdict: str          # "verified" | "hallucinated" | "insufficient" | "partially_true"
    confidence: float     # 0-100 — blended from NLI + LLM
    evidence_summary: str
    source: str
    correction: Optional[str] = None
    is_relevant: bool = True
    evidence_urls: List[str] = field(default_factory=list)
    primary_source_url: Optional[str] = None
    llm_reasoning: Optional[str] = None
    # Step 6/7 additions — NLI signal
    nli_label: Optional[str] = None    # "entailment" | "neutral" | "contradiction"
    nli_score: Optional[float] = None  # raw entailment probability 0-1


@dataclass
class ContentRelevanceResult:
    """Complete output of the content-relevance scorer."""
    topic_match_score: float                        # 0-1
    topic_match_label: str                          # "High" | "Medium" | "Low"
    off_topic_segments: List[OffTopicSegment]       # segments that diverged
    factual_accuracy: float                         # 0-1
    evidence_snippets: List[str]                    # key supporting quotes
    overall_content_score: int                      # 0-100 headline KPI
    claim_results: List[ClaimResult] = field(default_factory=list)

    # ── serialisation helper ──────────────────────────────────
    def to_api_dict(self) -> dict:
        """Shape consumed by the frontend GET endpoint."""
        return {
            "topic_match_score": round(self.topic_match_score, 4),
            "topic_match_label": self.topic_match_label,
            "off_topic_segments": [
                {"text": s.text, "start": s.start, "end": s.end, "score": round(s.score, 4)}
                for s in self.off_topic_segments
            ],
            "factual_accuracy": round(self.factual_accuracy, 4),
            "evidence_snippets": self.evidence_snippets,
            "claim_results": [
                {
                    "claim": c.claim,
                    "verdict": c.verdict,
                    "confidence": int(c.confidence),
                    "evidence_summary": c.evidence_summary,
                    "source": c.source,
                    "correction": c.correction,
                    "is_relevant": c.is_relevant,
                    "evidence_urls": c.evidence_urls,
                    "primary_source_url": c.primary_source_url,
                    "llm_reasoning": c.llm_reasoning,
                    "nli_label": c.nli_label,
                    "nli_score": round(c.nli_score, 4) if c.nli_score is not None else None,
                }
                for c in self.claim_results
            ],
            "overall_content_score": self.overall_content_score,
        }
