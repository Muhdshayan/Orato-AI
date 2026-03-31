"""
Content Relevance – Scorer
============================
Core NLP / LLM scoring logic.  No database imports, no FastAPI.
Independently testable: all external I/O goes through the LLM and
search clients injected at construction time.

Ported from the TruthForge evaluator + retriever + cleaner pipeline,
condensed into a single synchronous scoring pass suitable for
``asyncio.to_thread(...)`` execution.
"""

from __future__ import annotations

import json
import logging
import math
import re
from html import unescape
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from python_modules.content_relevance import config
from python_modules.content_relevance.models import (
    ClaimResult,
    ContentRelevanceResult,
    OffTopicSegment,
)

logger = logging.getLogger("content_relevance.scorer")

_SCRIPT_STYLE_RE = re.compile(r"(?is)<(script|style).*?>.*?</\\1>")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
# _NON_FACT_PATTERNS removed — filtering is now LLM-based (_llm_filter_claims)

# ---------------------------------------------------------------------------
# Lazy heavy imports — keep module import fast
# ---------------------------------------------------------------------------

_llm = None
_embeddings = None
_tavily_client = None
_reranker = None      # cross-encoder reranker (Step 5)
_nli_pipeline = None  # NLI entailment model  (Step 6)


def _get_llm():
    """Return a LangChain chat model based on provider config."""
    global _llm
    if _llm is not None:
        return _llm

    if config.LLM_PROVIDER == "groq":
        from langchain_groq import ChatGroq
        _llm = ChatGroq(
            model=config.GROQ_MODEL,
            api_key=config.GROQ_API_KEY,
            temperature=0,
        )
    else:
        from langchain_openai import ChatOpenAI
        _llm = ChatOpenAI(
            model=config.OPENAI_MODEL,
            api_key=config.OPENAI_API_KEY,
            temperature=0,
        )
    return _llm


def _get_embeddings():
    global _embeddings
    if _embeddings is not None:
        return _embeddings
    from langchain_huggingface import HuggingFaceEmbeddings
    _embeddings = HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    return _embeddings


def _get_tavily():
    global _tavily_client
    if _tavily_client is not None:
        return _tavily_client
    if config.TAVILY_API_KEY:
        try:
            from tavily import TavilyClient
            _tavily_client = TavilyClient(api_key=config.TAVILY_API_KEY)
        except ImportError:
            logger.warning("tavily package not installed; web search disabled")
    return _tavily_client


def _get_reranker():
    """Lazy-load the cross-encoder reranker (Step 5)."""
    global _reranker
    if _reranker is not None:
        return _reranker
    try:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(config.RERANKER_MODEL, max_length=512)
        logger.info("Reranker loaded: %s", config.RERANKER_MODEL)
    except Exception as exc:
        logger.warning("Reranker load failed (%s); reranking disabled", exc)
        _reranker = None
    return _reranker


def _get_nli():
    """Lazy-load the NLI entailment pipeline (Step 6)."""
    global _nli_pipeline
    if _nli_pipeline is not None:
        return _nli_pipeline
    try:
        from transformers import pipeline as hf_pipeline
        _nli_pipeline = hf_pipeline(
            "zero-shot-classification",
            model=config.NLI_MODEL,
            device=-1,  # CPU
        )
        logger.info("NLI pipeline loaded: %s", config.NLI_MODEL)
    except Exception as exc:
        logger.warning("NLI pipeline load failed (%s); NLI checks disabled", exc)
        _nli_pipeline = None
    return _nli_pipeline


# ═══════════════════════════════════════════════════════════════
# Helper: synchronous LLM call
# ═══════════════════════════════════════════════════════════════

def _llm_invoke(system: str, user: str) -> str:
    """Blocking call to the chat model.  Returns raw text."""
    from langchain_core.messages import HumanMessage, SystemMessage
    llm = _get_llm()
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return response.content


def _parse_json(text: str) -> Any:
    """Best-effort JSON extraction from an LLM response."""
    raw = (text or "").strip()
    candidates: List[str] = [raw]
    if "```json" in raw:
        candidates.append(raw.split("```json", 1)[1].split("```", 1)[0].strip())
    if "```" in raw:
        candidates.append(raw.split("```", 1)[1].split("```", 1)[0].strip())

    decoder = json.JSONDecoder()
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except Exception:
            pass
        for idx, ch in enumerate(candidate):
            if ch not in "[{":
                continue
            try:
                parsed, _ = decoder.raw_decode(candidate[idx:])
                return parsed
            except Exception:
                continue

    raise ValueError("Could not parse JSON from LLM response")


def _log_llm_failure(stage: str, raw: str, exc: Exception) -> None:
    if not config.LOG_LLM_FAILURES:
        return
    snippet = (raw or "").strip().replace("\n", "\\n")
    if len(snippet) > 1200:
        snippet = snippet[:1200] + "..."
    logger.warning(
        "LLM parse failed at %s: %s. Raw response: %s",
        stage,
        f"{type(exc).__name__}: {exc}",
        snippet,
    )


def _invoke_and_parse_json(system: str, user: str, stage: str) -> Any:
    raw = ""
    try:
        raw = _llm_invoke(system, user)
        return _parse_json(raw)
    except Exception as exc:
        _log_llm_failure(stage, raw, exc)
        raise


def _llm_filter_claims(claims: List[str], topic: str) -> List[str]:
    """
    Use the LLM to decide which claims are objectively verifiable external facts.
    Removes greetings, opinions, self-introductions, meta-statements, and questions.
    Falls back to keeping all non-empty claims if the LLM call fails.
    """
    if not claims:
        return []

    block = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))
    sys_prompt = (
        "You are a strict fact-checking filter. For each numbered claim decide: "
        "is it an objective, externally verifiable fact about the world?\n\n"
        "Return keep=false for ANY of the following — these are NOT facts:\n"
        "  - Greetings / salutations: 'Asalaakum', 'Hello', 'Hi', 'Good morning'\n"
        "  - Speaker introductions: 'My name is X', 'I am X', 'This is X speaking'\n"
        "  - Topic announcements: 'Today my topic is X', 'The topic is X', 'I will discuss X'\n"
        "  - Opinions / beliefs: 'I think', 'I believe', 'I feel', 'In my opinion'\n"
        "  - Vague praise or sentiment: 'Pakistan is great', 'It is very important'\n"
        "  - Questions: any sentence ending with ?\n\n"
        "Return keep=true ONLY for sentences that state a concrete external fact "
        "with specific names, places, dates, numbers, or historical events "
        "that a search engine could verify.\n\n"
        "EXAMPLES of keep=false:\n"
        "  'Asalaakum, my name is Ahmed.'  → keep=false  (greeting + introduction)\n"
        "  'Today the topic is Pakistan.'  → keep=false  (topic announcement)\n"
        "  'I think Pakistan is a great country.'  → keep=false  (opinion)\n\n"
        "EXAMPLES of keep=true:\n"
        "  'Pakistan was founded on 14 August 1947.'  → keep=true\n"
        "  'Pakistan has four provinces.'  → keep=true\n"
        "  'Muhammad Ali Jinnah was the founder of Pakistan.'  → keep=true\n\n"
        'Return strict JSON: {"results": [{"index": 1, "keep": true}, ...]}'
    )
    usr_prompt = f"TOPIC: {topic}\n\nCLAIMS TO FILTER:\n{block}"

    try:
        data = _invoke_and_parse_json(sys_prompt, usr_prompt, "claim_filtering")
        results = data.get("results", [])
        keep_indices = {
            int(r["index"])
            for r in results
            if isinstance(r, dict) and r.get("keep") is True
        }
        filtered = [
            claims[i - 1].strip()
            for i in sorted(keep_indices)
            if 1 <= i <= len(claims) and claims[i - 1].strip()
        ]
        filtered = list(dict.fromkeys(filtered))
        logger.info(
            "LLM filter: %d claims in → %d kept", len(claims), len(filtered)
        )
        return filtered
    except Exception as exc:
        logger.warning(
            "LLM claim filtering failed (%s); keeping all non-empty claims",
            type(exc).__name__,
        )
        return list(dict.fromkeys(c.strip() for c in claims if c.strip()))


def _is_obvious_non_fact_claim(claim: str, topic: str = "") -> bool:
    """
    Final safety guard for clearly non-factual transcript lines.
    Keeps this lightweight and non-regex so we only block obvious meta speech.
    """
    t = (claim or "").strip().lower()
    if not t:
        return True

    # Remove simple leading punctuation/noise to stabilize startswith checks.
    t = t.lstrip("-*#:. ").strip()

    bad_starts = (
        "assalam",
        "asala",
        "asalam",
        "hello",
        "hi ",
        "good morning",
        "good evening",
        "my name is",
        "i am ",
        "this is ",
        "today the topic is",
        "today my topic is",
        "the topic is",
        "our topic is",
        "i will talk about",
        "today i will talk about",
        "in this presentation",
        "in this video",
        "let us talk about",
        "let's talk about",
        "i have ",
        "i belong to",
        "i belong from",
        "i am from ",
        "i'm from ",
        "i finished ",
        "i finish ",
        "i completed ",
        "i like ",
        "i love ",
        "i enjoy ",
        "i play ",
        "i read ",
        "my favorite ",
        "my favourite ",
        "my hobby ",
        "my hobbies ",
        "i'm going to ",
        "i am going to ",
        "i will go ",
        "i plan to ",
        "i want to ",
        "my family ",
        "my father ",
        "my mother ",
        "my dad ",
        "my mom ",
        "my brother ",
        "my sister ",
        "my grandfather ",
        "my grandmother ",
        "my uncle ",
        "my aunt ",
        "my cousin ",
        "my parents ",
        "my son ",
        "my daughter ",
        "my wife ",
        "my husband ",
        "my friend ",
        "my friends ",
        "my school ",
        "my college ",
        "my university ",
        "my teacher ",
        "my house ",
        "my home ",
        "my city ",
        "my village ",
        "my country ",
        "my age ",
        "i was born ",
        "i grew up ",
        "i studied ",
        "i study ",
        "i live in ",
        "i lived in ",
        "i work at ",
        "i work in ",
        "i work as ",
        "i joined ",
        "i had joined ",
        "i have joined ",
        "i went to ",
        "i go to ",
        "i attend ",
        "i attended ",
        "i learned ",
        "i learn ",
        "i spoke ",
        "i speak ",
        "i taught ",
        "i teach ",
        "i moved to ",
        "i came to ",
        "i came from ",
        "i started ",
        "i passed ",
        "i got ",
        "i did ",
        "i do ",
        "i used to ",
        "i'm studying ",
        "i am studying ",
        "i'm working ",
        "i am working ",
        "i'm living ",
        "i am living ",
    )
    if t.startswith(bad_starts):
        return True

    # Broader rule: any sentence starting with "i" + past tense personal verb
    # about the speaker's own actions/life is unverifiable
    if re.match(r"^i\s+(had|have|was|am|did|do|can|could|would|should|will)\s", t):
        return True

    bad_contains = (
        " my name is ",
        " today the topic is ",
        " topic is ",
        " i will talk about ",
        " i belong to ",
        " i belong from ",
        " my favorite ",
        " my favourite ",
        " i have brothers",
        " i have sisters",
        " i have a brother",
        " i have a sister",
        " my family ",
        " my father ",
        " my mother ",
        " my grandfather ",
        " my grandmother ",
        " my parents ",
        " i joined ",
        " i had joined ",
        " i studied ",
        " i study ",
        " i live in ",
        " i lived in ",
        " i went to ",
        " i attend ",
        " i attended ",
    )
    if any(k in f" {t} " for k in bad_contains):
        return True

    topic_l = (topic or "").strip().lower()
    if topic_l and t in {
        f"today the topic is {topic_l}.",
        f"today my topic is {topic_l}.",
        f"the topic is {topic_l}.",
        f"topic is {topic_l}.",
    }:
        return True

    return False


def _strip_topic_prefix(claim: str) -> str:
    """Remove topic prefix like 'India context:' or 'Topic: X - ' from claim."""
    s = (claim or "").strip()
    # Match "X context:" or "X context :" at start (case-insensitive)
    m = re.match(r"^[\w\s]+context\s*:\s*", s, re.IGNORECASE)
    if m:
        s = s[m.end() :].strip()
    # Match "Topic: X - " or "Topic: X. "
    m = re.match(r"^topic\s*:\s*[^-]+-\s*", s, re.IGNORECASE)
    if m:
        s = s[m.end() :].strip()
    m = re.match(r"^topic\s*:\s*[^.]+\.\s*", s, re.IGNORECASE)
    if m:
        s = s[m.end() :].strip()
    # Match "In the context of X, " or "In context of X, "
    m = re.match(r"^in\s+(?:the\s+)?context\s+of\s+[^,]+,?\s*", s, re.IGNORECASE)
    if m:
        s = s[m.end() :].strip()
    return s


def _final_claim_sanity_filter(claims: List[str], topic: str) -> List[str]:
    """Drop obvious non-fact/meta claims that should never be web-checked."""
    kept: List[str] = []
    removed = 0
    for c in claims:
        s = (c or "").strip()
        if not s:
            continue
        if _is_obvious_non_fact_claim(s, topic):
            removed += 1
            continue
        kept.append(s)
    deduped = list(dict.fromkeys(kept))
    if removed:
        logger.info("Final claim sanity filter removed %d obvious non-fact claims", removed)
    return deduped


# ═══════════════════════════════════════════════════════════════
# Stage 1: Claim extraction (text → atomic claims)
# ═══════════════════════════════════════════════════════════════

_FILLER_RE = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bum+\b", r"\buh+\b", r"\bah+\b", r"\ber+\b",
        r"\blike,?\s+", r"\byou know,?\s+", r"\bi mean,?\s+",
        r"\bbasically,?\s+", r"\bactually,?\s+", r"\bliterally,?\s+",
        r"\bso+,?\s+(?=\w)", r"\bwell,?\s+(?=\w)",
    ]
]


def _preprocess(text: str) -> str:
    out = text
    for pat in _FILLER_RE:
        out = pat.sub(" ", out)
    out = re.sub(r" +", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return "\n".join(line.strip() for line in out.split("\n")).strip()


def extract_claims(text: str, topic: str) -> Tuple[str, List[str]]:
    """Return (cleaned_text, list_of_atomic_claims)."""
    preprocessed = _preprocess(text[: config.MAX_TEXT_CHARS])

    sys_prompt = (
        "You are a transcript analyst for a fact-checking pipeline.\n\n"
        "Your ONLY job is to IDENTIFY and COPY the factual claims the speaker made — "
        "word-for-word (or very close). You are NOT a fact-checker and must NEVER correct anything.\n\n"
        "TASK:\n"
        "1. COREFERENCE RESOLUTION: replace pronouns (he/she/it/they/this) with the subject "
        "from context — but do NOT change names, numbers, dates, or any factual content.\n"
        "2. CLAIM EXTRACTION: copy every concrete statement the speaker asserted as a fact, "
        "exactly as they said it — even if you know it is wrong.\n\n"
        "CRITICAL — NEVER do any of the following:\n"
        "  - Correct a wrong number  (e.g. if speaker says 'ten provinces', keep 'ten provinces')\n"
        "  - Fix a wrong date        (e.g. if speaker says 'founded in 1950', keep '1950')\n"
        "  - Replace a wrong name   (e.g. if speaker says 'Narendra Modi founded Pakistan', "
        "keep 'Narendra Modi' — do NOT swap it for the correct founder)\n"
        "  - Add any fact the speaker did not say\n\n"
        "ALSO do NOT extract:\n"
        "  - Greetings / salutations  ('Asalaakum', 'Hello everyone')\n"
        "  - Speaker self-introductions  ('My name is X', 'I am X')\n"
        "  - Topic announcements  ('Today my topic is X', 'I will talk about X')\n"
        "  - Opinions  ('I think', 'I believe')\n"
        "  - Vague statements with no checkable content\n"
        "  - Questions\n"
        "  - Personal biographical facts about the speaker  "
        "('I have two brothers', 'I belong to Rawalpindi', 'I finished my studies', "
        "'My family includes my grandmother', 'My father is a teacher')  "
        "— these are unverifiable private facts, not public claims\n"
        "  - Personal experiences, education, or affiliations  "
        "('I joined Ishaal English house', 'I study at XYZ school', "
        "'I had joined a coaching center', 'I learned English at ABC institute', "
        "'I went to government school', 'I live in Islamabad')  "
        "— these are the speaker's own life events, no public source can verify them\n"
        "  - Future intentions or plans  "
        "('I am going abroad', 'I will join X', 'I plan to do Y')  "
        "— these are not factual assertions about the present or past\n"
        "  - Personal habits, hobbies, or preferences  "
        "('I like reading', 'my favorite thing is X', 'I play cricket')  "
        "— these are subjective and privately held\n"
        "  - Any statement where the subject is 'I' or 'my'  "
        "— almost always personal and unverifiable by external sources\n"
        "  - Any claim that can ONLY be verified by the speaker themselves  "
        "— if no public source could confirm or deny it, skip it\n\n"
        "Mental test before extracting: 'Could a search engine or encyclopedia "
        "verify this independently of the speaker?' If NO, do not extract it.\n\n"
        "The purpose is: extract the speaker's claims exactly so we can verify them against "
        "external evidence and find which ones are wrong.\n\n"
        f"Presentation topic: {topic}"
    )
    usr_prompt = (
        "Extract claims from this transcript and respond in strict JSON:\n"
        '{"cleaned_text": "...", "claims": ["Claim as speaker said it", ...], '
        '"entities_found": ["E1", ...]}\n\n'
        f"TRANSCRIPT:\n{preprocessed}"
    )

    try:
        data = _invoke_and_parse_json(sys_prompt, usr_prompt, "claim_extraction")
        cleaned = data.get("cleaned_text", preprocessed)
        claims = data.get("claims", [])
    except Exception:
        logger.warning("LLM claim extraction failed; falling back to heuristic")
        cleaned = preprocessed
        claims = _heuristic_claims(preprocessed, topic)

    # Atomic splitting
    atomic = _split_atomic(claims, topic)

    # Step 3a: Remove only obvious non-facts (greetings, intros, topic announcements).
    # LLM filter disabled — it was rejecting valid factual claims (e.g. India/Pakistan facts).
    filtered = _final_claim_sanity_filter(atomic, topic)

    # If sanity filter removed everything, keep atomic (avoid losing all claims)
    if not filtered and atomic:
        logger.warning(
            "Sanity filter removed all %d claims; keeping them for fact-checking",
            len(atomic),
        )
        filtered = atomic

    # Step 3b: Normalize claims (entity resolution + self-contained rewriting)
    normalized = _normalize_claims(filtered[: config.MAX_CLAIMS], topic)
    final_claims = _final_claim_sanity_filter(normalized, topic)

    return cleaned, final_claims[: config.MAX_CLAIMS]


def _heuristic_claims(text: str, topic: str = "") -> List[str]:
    """
    LLM-based fallback claim extractor used when the primary extraction fails.
    Asks the LLM to extract factual sentences directly from raw text.
    Falls back to simple sentence splitting only if the LLM also fails.
    """
    if not text.strip():
        return []

    sys_prompt = (
        "Extract concrete factual statements from the transcript below.\n\n"
        "Copy each claim EXACTLY as the speaker said it — even if the fact is wrong. "
        "Do NOT correct dates, names, numbers, or any content. "
        "Ignore greetings, self-introductions, topic announcements, opinions, "
        "and vague statements.\n"
        "Also ignore personal biographical facts ('I have two brothers', 'I belong to X'), "
        "personal experiences/education ('I joined X institute', 'I study at Y school'), "
        "future intentions ('I am going abroad'), and personal habits/preferences "
        "('I like reading'). Drop any statement where the subject is 'I' or 'my'. "
        "Only extract claims a search engine could verify.\n"
        'Return strict JSON: {"claims": ["claim as stated 1", "claim as stated 2", ...]}'
    )
    usr_prompt = (
        f"TOPIC: {topic}\n\nTEXT:\n{text[:3000]}"
        if topic else f"TEXT:\n{text[:3000]}"
    )

    try:
        data = _invoke_and_parse_json(sys_prompt, usr_prompt, "heuristic_claims_llm")
        claims = data.get("claims", [])
        if isinstance(claims, list) and claims:
            return [c.strip() for c in claims if isinstance(c, str) and c.strip()][:20]
    except Exception as exc:
        logger.warning("LLM heuristic claims failed (%s); using sentence split", type(exc).__name__)

    # Last-resort: simple sentence split (no regex logic decisions)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) >= 20][:20]


def _split_atomic(claims: List[str], topic: str) -> List[str]:
    if not claims:
        return []
    block = "\n".join(f"- {c}" for c in claims[:config.MAX_CLAIMS])
    sys_prompt = (
        "Split compound claims so each output sentence contains exactly ONE checkable assertion.\n\n"
        "STRICT RULES:\n"
        "  - Copy names, numbers, dates, and quantities EXACTLY as given — "
        "even if they are factually wrong. Do NOT correct them.\n"
        "  - If a claim says '1950', keep '1950'. If it says 'ten provinces', keep 'ten'. "
        "If it says 'Narendra Modi', keep 'Narendra Modi'.\n"
        "  - Only split; never rewrite the factual content.\n"
        "  - Silently DROP items that are greetings, self-introductions, topic announcements, "
        "opinions, or vague statements with no checkable content.\n"
        "  - Also DROP personal biographical facts ('I have two brothers', 'I belong to X'), "
        "personal experiences/education ('I joined Ishaal English house', 'I study at X school'), "
        "future intentions ('I am going abroad'), and personal habits/preferences "
        "('I like reading', 'my favorite thing is X').\n"
        "  - DROP any statement where the subject is 'I' or 'my' — these are personal.\n"
        "  - Only keep claims a search engine could verify independently of the speaker."
    )
    usr_prompt = (
        f"Topic: {topic}\n\nClaims (split only — do NOT fix facts):\n{block}\n\n"
        'Return strict JSON: {"atomic_claims": ["...", ...]}'
    )
    try:
        data = _invoke_and_parse_json(sys_prompt, usr_prompt, "claim_atomic_split")
        out = data.get("atomic_claims") or data.get("claims") or []
        if isinstance(out, list):
            return list(dict.fromkeys(s.strip() for s in out if isinstance(s, str) and s.strip()))
    except Exception:
        pass
    return list(dict.fromkeys(c.strip() for c in claims if c.strip()))


# ═══════════════════════════════════════════════════════════════
# Stage 1b: Claim Normalization (Step 3 of pipeline)
#   Resolves vague pronouns → named entities.
#   Rewrites each claim as a self-contained, web-searchable statement.
# ═══════════════════════════════════════════════════════════════

def _normalize_claims(claims: List[str], topic: str) -> List[str]:
    """
    Convert each claim into a fully self-contained verifiable statement.
    Pronouns are replaced with named entities; implicit context is made explicit.
    Falls back to the original list if the LLM call fails.
    """
    if not claims:
        return []

    block = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))
    sys_prompt = (
        "You are a claim normalizer for a fact-checking pipeline.\n\n"
        "For each numbered claim make it self-contained so it can be searched independently.\n\n"
        "ALLOWED changes:\n"
        "  - Replace pronouns (he/she/it/they/this/that) with the named entity from context.\n\n"
        "FORBIDDEN changes — NEVER do these:\n"
        "  - Add topic prefix (e.g. 'India context:', 'Topic: Pakistan', 'In the context of X')\n"
        "  - Prepend or wrap the claim with the declared topic\n"
        "  - Change any number, count, or quantity  "
        "(if claim says 'ten provinces', keep 'ten provinces')\n"
        "  - Change any date or year  "
        "(if claim says '1950', keep '1950' — do NOT write '1947')\n"
        "  - Change any person's name  "
        "(if claim says 'Narendra Modi founded Pakistan', keep 'Narendra Modi')\n"
        "  - Add facts the original claim does not contain\n"
        "  - Fix or improve factual accuracy in any way\n\n"
        "ALSO: if a claim is a personal biographical fact ('I have two brothers'), "
        "a personal experience/education ('I joined X institute', 'I study at Y'), "
        "a future intention ('I am going abroad'), or a personal preference/habit "
        "('I like reading'), replace it with the string \"SKIP\" in the output array. "
        "Any statement where the subject is 'I' or 'my' should be SKIPped. "
        "These are unverifiable by any public source.\n\n"
        "The claims may contain errors — that is intentional, we need to verify them as-stated.\n\n"
        "Return strict JSON: {\"normalized\": [\"claim 1\", \"claim 2\", ...]}\n"
        "Output list must be the SAME length as the input list (use \"SKIP\" for dropped claims)."
    )
    usr_prompt = f"TOPIC: {topic}\n\nCLAIMS TO NORMALIZE (do not fix facts):\n{block}"
    try:
        data = _invoke_and_parse_json(sys_prompt, usr_prompt, "claim_normalization")
        normalized = data.get("normalized", [])
        if isinstance(normalized, list) and len(normalized) == len(claims):
            result = [
                _strip_topic_prefix(s.strip())
                for s in normalized
                if isinstance(s, str) and s.strip() and s.strip().upper() != "SKIP"
            ]
            if result:
                logger.info("Claim normalization: %d → %d claims (dropped %d personal/unverifiable)",
                            len(claims), len(result), len(claims) - len(result))
                return result
    except Exception as exc:
        logger.warning("Claim normalization failed (%s); using original claims", type(exc).__name__)
    return claims


# ═══════════════════════════════════════════════════════════════
# Stage 2: Evidence retrieval (web search → FAISS index)
# ═══════════════════════════════════════════════════════════════

def _generate_queries(claims: List[str], topic: str) -> List[str]:
    block = "\n".join(f"- {c}" for c in claims[:10])
    sys_prompt = (
        "Generate focused search queries for fact-checking.\n"
        'Return JSON: {"primary_queries": [], "fallback_queries": []}'
    )
    usr_prompt = f"Topic: {{topic}}\n\nClaims:\n{{block}}\n\nGenerate up to {config.NUM_SEARCH_QUERIES} queries."
    try:
        data = _invoke_and_parse_json(
            sys_prompt,
            usr_prompt.format(topic=topic, block=block),
            "query_generation",
        )
        primary = data.get("primary_queries", [])
        fallback = data.get("fallback_queries", [])
        combined = primary[:4] + fallback[:2]
        return list(dict.fromkeys(q for q in combined if q))[:config.NUM_SEARCH_QUERIES]
    except Exception:
        return [topic, f"{topic} facts", f"{topic} overview"][:config.NUM_SEARCH_QUERIES]


def _claim_queries(claims: List[str]) -> List[str]:
    """Generate direct web queries so each extracted claim gets explicit retrieval."""
    queries: List[str] = []
    for claim in claims[: config.MAX_CLAIM_QUERIES]:
        cleaned = re.sub(r"\s+", " ", claim).strip()
        if not cleaned:
            continue
        clipped = cleaned[:180]
        queries.append(clipped)
        queries.append(f"{clipped} source")
    return queries


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    return url.strip().rstrip("/").split("#", 1)[0]


def _html_to_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    cleaned = _SCRIPT_STYLE_RE.sub(" ", raw_html)
    cleaned = _TAG_RE.sub(" ", cleaned)
    cleaned = unescape(cleaned)
    return _WS_RE.sub(" ", cleaned).strip()


def _scrape_url_text(url: str) -> str:
    """Fetch and clean webpage text for richer, fresher evidence context."""
    normalized = _normalize_url(url)
    if not normalized.startswith(("http://", "https://")):
        return ""

    try:
        req = Request(
            normalized,
            headers={"User-Agent": "Mozilla/5.0 (compatible; OratoAI-FactCheck/1.0)"},
        )
        with urlopen(req, timeout=config.SCRAPE_TIMEOUT_SECONDS) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "html" not in content_type:
                return ""
            raw = response.read(config.MAX_SCRAPED_CHARS * 3)
        text = _html_to_text(raw.decode("utf-8", errors="ignore"))
        return text[: config.MAX_SCRAPED_CHARS]
    except Exception:
        return ""


def _enrich_with_scraped_pages(documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Replace short snippets with scraped page content for a subset of URLs."""
    if not documents:
        return []

    enriched: List[Dict[str, str]] = []
    scraped = 0
    for doc in documents:
        updated = dict(doc)
        body = (updated.get("content") or "").strip()
        url = updated.get("url", "")

        should_scrape = (
            scraped < config.MAX_SCRAPED_PAGES
            and _normalize_url(url).startswith(("http://", "https://"))
            and len(body) < 450
        )
        if should_scrape:
            scraped_text = _scrape_url_text(url)
            if scraped_text:
                body = f"{body}\n\n{scraped_text}" if body else scraped_text
                scraped += 1

        updated["content"] = body[: config.MAX_SCRAPED_CHARS]
        enriched.append(updated)

    if scraped:
        logger.info("Enriched %d evidence documents with scraped page text", scraped)
    return enriched


def _search_tavily(query: str) -> List[Dict[str, str]]:
    client = _get_tavily()
    if client is None:
        return []
    try:
        resp = client.search(query=query, search_depth="basic", max_results=config.MAX_SEARCH_RESULTS, include_answer=True)
        docs: List[Dict[str, str]] = []
        if resp.get("answer"):
            docs.append({"content": resp["answer"], "source": "Tavily AI", "url": "tavily_answer"})
        for r in resp.get("results", []):
            docs.append({
                "content": r.get("content", ""),
                "source": (r.get("url", "").split("/")[2] if r.get("url") else "Unknown"),
                "url": r.get("url", ""),
            })
        return docs
    except Exception as exc:
        logger.error("Tavily search failed: %s", exc)
        return []


def _search_duckduckgo(query: str) -> List[Dict[str, str]]:
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            try:
                results = list(
                    ddgs.text(
                        query,
                        max_results=config.MAX_SEARCH_RESULTS,
                        backend="lite",
                    )
                )
            except TypeError:
                results = list(ddgs.text(query, max_results=config.MAX_SEARCH_RESULTS))
        return [
            {
                "content": r.get("body", ""),
                "source": (urlparse(r.get("href", "")).netloc if r.get("href") else "Unknown"),
                "url": r.get("href", ""),
            }
            for r in results
            if r.get("body") or r.get("href")
        ]
    except Exception as exc:
        logger.error("DuckDuckGo search failed: %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════
# Stage 2b: Wikipedia dedicated retriever (Step 4 of pipeline)
# ═══════════════════════════════════════════════════════════════

def _search_wikipedia(query: str) -> List[Dict[str, str]]:
    """
    Query the Wikipedia search API and return page extracts for the top hits.
    Uses only the free public API — no key required.
    """
    import json as _json
    from urllib.parse import urlencode

    docs: List[Dict[str, str]] = []
    try:
        # Step 1: find matching page titles
        search_params = urlencode({
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": config.WIKIPEDIA_MAX_RESULTS,
            "format": "json",
            "srprop": "snippet",
        })
        search_url = f"https://en.wikipedia.org/w/api.php?{search_params}"
        req = Request(search_url, headers={"User-Agent": "OratoAI-FactCheck/1.0 (educational)"})
        with urlopen(req, timeout=config.WIKIPEDIA_TIMEOUT_SECONDS) as resp:
            search_data = _json.loads(resp.read().decode("utf-8"))

        hits = search_data.get("query", {}).get("search", [])
        titles = [h["title"] for h in hits if h.get("title")]

        if not titles:
            return []

        # Step 2: fetch page extracts for matching titles
        extract_params = urlencode({
            "action": "query",
            "prop": "extracts",
            "exintro": "1",       # intro section only
            "explaintext": "1",   # plain text
            "titles": "|".join(titles[:config.WIKIPEDIA_MAX_RESULTS]),
            "format": "json",
        })
        extract_url = f"https://en.wikipedia.org/w/api.php?{extract_params}"
        req2 = Request(extract_url, headers={"User-Agent": "OratoAI-FactCheck/1.0 (educational)"})
        with urlopen(req2, timeout=config.WIKIPEDIA_TIMEOUT_SECONDS) as resp2:
            extract_data = _json.loads(resp2.read().decode("utf-8"))

        pages = extract_data.get("query", {}).get("pages", {})
        for page in pages.values():
            title = page.get("title", "")
            extract = (page.get("extract") or "").strip()
            if not extract:
                continue
            wiki_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
            docs.append({
                "content": extract[: config.MAX_SCRAPED_CHARS],
                "source": "wikipedia.org",
                "url": wiki_url,
            })

        if docs:
            logger.info("Wikipedia retrieved %d pages for query: %s", len(docs), query[:80])

    except Exception as exc:
        logger.warning("Wikipedia search failed for %r: %s", query[:60], exc)

    return docs


def _embedding_similarity(a: str, b: str) -> float | None:
    try:
        embeddings = _get_embeddings()
        vec_a = embeddings.embed_query(a)
        vec_b = embeddings.embed_query(b)
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return None
        dot = sum(x * y for x, y in zip(vec_a, vec_b))
        norm = math.sqrt(sum(x * x for x in vec_a)) * math.sqrt(sum(y * y for y in vec_b))
        if norm == 0:
            return None
        return max(0.0, min(1.0, dot / norm))
    except Exception:
        return None


def _fallback_topic_relevance(claims: List[str], topic: str, text: str) -> float:
    """
    LLM-based fallback for topic relevance scoring.
    Used when the primary evaluate_topic_relevance LLM call fails.
    Uses a shorter, simpler prompt. Falls back to embedding similarity if this also fails.
    """
    if not topic:
        return 0.0

    sample_text = (
        " ".join(claims[:8]).strip()
        or (text or "").strip()[:1500]
    )
    if not sample_text:
        return 0.0

    sys_prompt = (
        "Rate how relevant the text is to the given topic on a scale of 0 to 100. "
        "100 = entirely about the topic, 0 = completely unrelated. "
        'Return only JSON: {"score": <number>}'
    )
    usr_prompt = f"TOPIC: {topic}\n\nTEXT SAMPLE:\n{sample_text[:1500]}"

    try:
        data = _invoke_and_parse_json(sys_prompt, usr_prompt, "fallback_topic_relevance")
        raw = data.get("score")
        if raw is not None:
            return max(0.0, min(1.0, float(raw) / 100))
    except Exception as exc:
        logger.warning("Fallback topic relevance LLM failed (%s); using embedding similarity", type(exc).__name__)

    # Last resort: embedding cosine similarity between topic and text blob
    sim = _embedding_similarity(topic, sample_text[:1000])
    return sim if sim is not None else 0.0


def _heuristic_judge_claim(claim: str, contexts: List[Dict], evidence_urls: List[str]) -> ClaimResult:
    """
    LLM-based fallback judge used when the primary _judge_claim LLM call fails.
    Uses a simpler, more direct prompt with less strict JSON requirements.
    Falls back to 'insufficient' verdict if this also fails.
    """
    if not contexts:
        return ClaimResult(
            claim=claim,
            verdict="insufficient",
            confidence=25,
            evidence_summary="No retrievable web evidence was found for this claim.",
            source="System",
            evidence_urls=evidence_urls,
            primary_source_url=evidence_urls[0] if evidence_urls else None,
            llm_reasoning="No supporting web evidence was retrieved, so the claim cannot be verified.",
        )

    evidence_text = "\n\n".join(
        f"[Source {i}] {c.get('source', '?')}:\n{(c.get('content') or '')[:400]}"
        for i, c in enumerate(contexts[:3], 1)
    )
    sys_prompt = (
        "You are a fact-checker. Based on the evidence, judge the claim.\n"
        "Be concise. Return JSON with these exact keys:\n"
        '{"verdict": "verified"|"partially_true"|"insufficient"|"hallucinated", '
        '"confidence": 0-100, "summary": "one sentence explanation", '
        '"reasoning": "1-3 sentences explaining why this claim is fact/not-fact from evidence"}'
    )
    usr_prompt = f'CLAIM: "{claim}"\n\nEVIDENCE:\n{evidence_text}'

    try:
        data = _invoke_and_parse_json(sys_prompt, usr_prompt, "fallback_judge")
        verdict = str(data.get("verdict", "insufficient")).lower()
        verdict = {
            "true": "verified", "false": "hallucinated",
            "mostly_true": "partially_true", "not_enough_info": "insufficient",
        }.get(verdict, verdict)
        if verdict not in {"verified", "hallucinated", "insufficient", "partially_true"}:
            verdict = "insufficient"
        src = contexts[0].get("source", "Unknown") if contexts else "System"
        return ClaimResult(
            claim=claim,
            verdict=verdict,
            confidence=max(0, min(100, int(data.get("confidence", 40)))),
            evidence_summary=data.get("summary", ""),
            source=src,
            evidence_urls=evidence_urls,
            primary_source_url=evidence_urls[0] if evidence_urls else None,
            llm_reasoning=(data.get("reasoning") or data.get("summary") or "").strip() or None,
        )
    except Exception as exc:
        logger.warning("Fallback LLM judge also failed (%s); returning insufficient", type(exc).__name__)
        src = contexts[0].get("source", "Unknown") if contexts else "System"
        snippet = (contexts[0].get("content", "") or "").strip()[:200] if contexts else ""
        return ClaimResult(
            claim=claim,
            verdict="insufficient",
            confidence=30,
            evidence_summary=f"Could not verify this claim. Best available evidence: {snippet}",
            source=src,
            evidence_urls=evidence_urls,
            primary_source_url=evidence_urls[0] if evidence_urls else None,
            llm_reasoning="Judgement fallback failed; returning insufficient due to weak or incomplete evidence.",
        )


def gather_evidence(claims: List[str], topic: str) -> List[Dict[str, str]]:
    """
    Run multi-source retrieval (Step 4) and return a deduplicated document list.
    Sources: Tavily → DuckDuckGo (web) + Wikipedia (dedicated channel).
    """
    generated = _generate_queries(claims, topic)
    claim_specific = _claim_queries(claims)
    queries = list(dict.fromkeys(generated + claim_specific))[: config.MAX_TOTAL_QUERIES]

    docs: List[Dict[str, str]] = []

    # Channel 1: Web search (Tavily preferred, DuckDuckGo fallback)
    for q in queries:
        hits = _search_tavily(q) or _search_duckduckgo(q)
        docs.extend(hits)

    # Channel 2: Wikipedia — query with topic + first few claim keywords
    wiki_queries: List[str] = [topic] + [
        " ".join(c.split()[:8]) for c in claims[:4]
    ]
    for wq in list(dict.fromkeys(wiki_queries))[:config.WIKIPEDIA_MAX_RESULTS + 1]:
        docs.extend(_search_wikipedia(wq))

    seen: set[Tuple[str, str]] = set()
    unique: List[Dict[str, str]] = []
    for d in docs:
        url = _normalize_url(d.get("url", ""))
        content = (d.get("content") or "").strip()
        key = (url, content[:140])
        if key in seen:
            continue
        seen.add(key)
        unique.append({
            "content": content,
            "source": d.get("source", "Unknown"),
            "url": url,
        })

    logger.info(
        "gather_evidence: %d unique docs collected (%d web + Wikipedia)",
        len(unique), len(unique),
    )
    return _enrich_with_scraped_pages(unique)


def _build_faiss(documents: List[Dict[str, str]]):
    """Build and return a FAISS vector store, or None."""
    if not documents:
        return None
    try:
        from langchain_core.documents import Document as LCDoc
        from langchain_community.vectorstores import FAISS
        lc_docs = [
            LCDoc(page_content=d["content"], metadata={"source": d.get("source", ""), "url": d.get("url", "")})
            for d in documents if d.get("content")
        ]
        if not lc_docs:
            return None
        return FAISS.from_documents(lc_docs, _get_embeddings())
    except Exception as exc:
        logger.error("FAISS build failed: %s", exc)
        return None


def _vector_search(store, query: str, k: int = 3) -> List[Dict]:
    if store is None:
        return []
    try:
        results = store.similarity_search_with_score(query, k=k)
        out: List[Dict] = []
        for doc, score in results:
            similarity = max(0.0, min(1.0, 1 - float(score))) if score is not None else 0.5
            out.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "url": doc.metadata.get("url", ""),
                "similarity_score": similarity,
            })
        return out
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
# Stage 2c: Cross-encoder reranker (Step 5 of pipeline)
# ═══════════════════════════════════════════════════════════════

def _rerank_evidence(claim: str, docs: List[Dict], top_k: int | None = None) -> List[Dict]:
    """
    Re-score ``docs`` against ``claim`` using a cross-encoder relevance model.
    Returns the top-k docs sorted by rerank score (highest first).
    Falls back to the original order when the model is unavailable.
    """
    if not docs:
        return []

    k = top_k if top_k is not None else config.RERANKER_TOP_K
    reranker = _get_reranker()

    if reranker is None:
        return docs[:k]

    try:
        pairs = [(claim, (d.get("content") or "")[:512]) for d in docs]
        scores = reranker.predict(pairs)
        scored = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
        reranked = []
        for rank_score, doc in scored[:k]:
            updated = dict(doc)
            updated["rerank_score"] = float(rank_score)
            reranked.append(updated)
        logger.debug(
            "Reranked %d → %d docs for claim: %s…", len(docs), len(reranked), claim[:60]
        )
        return reranked
    except Exception as exc:
        logger.warning("Reranking failed (%s); using original order", exc)
        return docs[:k]


# ═══════════════════════════════════════════════════════════════
# Stage 3: Evidence quality scoring
# ═══════════════════════════════════════════════════════════════

def score_evidence_quality(evidence: List[Dict]) -> Tuple[float, str]:
    """Return (quality_score 0-100, label NONE|LOW|MEDIUM|HIGH)."""
    if not evidence:
        return 0.0, "NONE"
    sims = [e.get("similarity_score", 0.5) for e in evidence]
    avg_sim = sum(sims) / len(sims)
    auth_hits = sum(
        1 for e in evidence
        if any(dom in (e.get("url", "") or e.get("source", "")) for dom in config.AUTHORITY_DOMAINS)
    )
    auth_ratio = auth_hits / len(evidence)
    score = (avg_sim * 0.4 + auth_ratio * 0.6) * 100
    if score >= 70:
        return score, "HIGH"
    if score >= 40:
        return score, "MEDIUM"
    if score > 0:
        return score, "LOW"
    return 0.0, "NONE"


# ═══════════════════════════════════════════════════════════════
# Stage 3b: NLI-based claim verification (Step 6 of pipeline)
# ═══════════════════════════════════════════════════════════════

def _nli_check(claim: str, evidence_text: str) -> Dict[str, Any]:
    """
    Run Natural Language Inference (NLI) to determine whether the evidence
    entails, contradicts, or is neutral toward the claim.

    Returns a dict with keys:
        label  – "entailment" | "neutral" | "contradiction"
        score  – probability of the winning label (0-1)
        scores – {label: probability} for all three classes
    Falls back to {"label": "neutral", "score": 0.5, "scores": {}} on error.
    """
    _default = {"label": "neutral", "score": 0.5, "scores": {}}

    if not claim or not evidence_text:
        return _default

    nli = _get_nli()
    if nli is None:
        return _default

    try:
        candidate_labels = ["entailment", "neutral", "contradiction"]
        # Truncate to avoid exceeding model max-length
        premise = evidence_text[:1200]
        result = nli(
            f"Premise: {premise}\nHypothesis: {claim}",
            candidate_labels,
            hypothesis_template="{}",
            multi_label=False,
        )
        # zero-shot-classification returns labels sorted by score descending
        label_scores = dict(zip(result["labels"], result["scores"]))
        best_label = result["labels"][0]
        best_score = result["scores"][0]
        logger.debug(
            "NLI for claim %r → %s (%.2f)", claim[:60], best_label, best_score
        )
        return {"label": best_label, "score": best_score, "scores": label_scores}
    except Exception as exc:
        logger.warning("NLI check failed (%s)", exc)
        return _default


# ═══════════════════════════════════════════════════════════════
# Stage 4: Per-claim LLM evaluation
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# Stage 4b: Confidence blending (Step 7 of pipeline)
# ═══════════════════════════════════════════════════════════════

def _blend_confidence(
    llm_verdict: str,
    llm_conf: int,
    nli_label: str,
    nli_score: float,
) -> Tuple[str, int]:
    """
    Merge LLM verdict/confidence with NLI entailment signal.

    Blending rules
    --------------
    NLI=entailment   + LLM=verified      → strong confirmation: boost confidence by 10%
    NLI=contradiction + LLM=verified     → conflict: downgrade verdict to "partially_true",
                                           reduce confidence
    NLI=entailment   + LLM=hallucinated  → NLI disagrees: upgrade verdict to "insufficient"
    NLI=contradiction + LLM=hallucinated → both agree claim is wrong: boost confidence
    All other combos                     → weighted blend of NLI score and LLM confidence

    Returns (final_verdict, final_confidence 0-100).
    """
    nli_conf_pct = int(round(nli_score * 100))

    # NLI agrees claim is supported
    if nli_label == "entailment" and llm_verdict == "verified":
        blended = min(100, int(round(llm_conf * 0.6 + nli_conf_pct * 0.4)) + 10)
        return "verified", blended

    # NLI disagrees with LLM "verified" verdict
    if nli_label == "contradiction" and llm_verdict == "verified":
        blended = max(0, int(round(llm_conf * 0.4 + (100 - nli_conf_pct) * 0.6)) - 10)
        return "partially_true", blended

    # NLI says claim IS supported but LLM called it hallucinated
    if nli_label == "entailment" and llm_verdict == "hallucinated":
        blended = int(round(llm_conf * 0.3 + nli_conf_pct * 0.7))
        return "insufficient", blended

    # Both signals agree the claim is unsupported/false
    if nli_label == "contradiction" and llm_verdict == "hallucinated":
        blended = min(100, int(round(llm_conf * 0.5 + nli_conf_pct * 0.5)) + 5)
        return "hallucinated", blended

    # NLI is neutral or partially confirming — weighted blend
    nli_weight = 0.35
    llm_weight = 0.65
    blended = int(round(llm_conf * llm_weight + nli_conf_pct * nli_weight))
    return llm_verdict, max(0, min(100, blended))


def _judge_claim(
    claim: str,
    contexts: List[Dict],
    topic: str,
    quality_level: str,
    nli_result: Dict | None = None,
) -> ClaimResult:
    """
    Hybrid claim verdict using:
      1. LLM reasoning over retrieved evidence
      2. NLI entailment signal (Step 6)
      3. Blended confidence (Step 7)
    """
    evidence_text = (
        "\n\n".join(
            f"[Source {i}] {c.get('source','?')}:\n{c['content'][:500]}"
            for i, c in enumerate(contexts, 1)
        )
        if contexts
        else "No evidence found."
    )

    if quality_level == "NONE":
        sys = (
            "You are a fact-checking judge. No usable evidence was found.\n"
            "Return JSON: {\"verdict\":\"insufficient\"|\"hallucinated\", "
            "\"confidence\":20-60, \"evidence_summary\":\"...\", "
            "\"reasoning\":\"1-3 sentences on why this is fact/not-fact\", \"correction\":\"\"}"
        )
    elif quality_level == "LOW":
        sys = (
            "You are a fact-checking judge working with LOW-quality evidence.\n"
            "Return JSON: {\"verdict\":\"verified\"|\"partially_true\"|\"insufficient\"|\"hallucinated\", "
            "\"confidence\":40-80, \"evidence_summary\":\"...\", "
            "\"reasoning\":\"1-3 sentences on why this is fact/not-fact\", \"correction\":\"\"}"
        )
    else:
        sys = (
            "You are an impartial fact-checking judge.\n"
            "Return JSON: {\"verdict\":\"verified\"|\"partially_true\"|\"hallucinated\"|\"insufficient\", "
            "\"confidence\":0-100, \"evidence_summary\":\"...\", "
            "\"reasoning\":\"1-3 sentences on why this is fact/not-fact\", \"correction\":\"\"}"
        )

    usr = f"TOPIC: {topic}\nCLAIM: \"{claim}\"\nEVIDENCE:\n{evidence_text}\n\nJudge as JSON."
    evidence_urls = list(dict.fromkeys(
        _normalize_url(c.get("url", ""))
        for c in contexts
        if _normalize_url(c.get("url", "")).startswith(("http://", "https://"))
    ))

    # Unpack NLI result (may be None if model unavailable)
    nli_label = (nli_result or {}).get("label", "neutral")
    nli_score_val = (nli_result or {}).get("score", 0.5)

    try:
        data = _invoke_and_parse_json(sys, usr, "claim_judgement")
        llm_verdict = data.get("verdict", "insufficient").lower()
        llm_verdict = {
            "true": "verified",
            "false": "hallucinated",
            "mostly_true": "partially_true",
            "partially true": "partially_true",
            "not_enough_info": "insufficient",
            "unsupported": "insufficient",
        }.get(llm_verdict, llm_verdict)
        if llm_verdict not in {"verified", "hallucinated", "insufficient", "partially_true"}:
            llm_verdict = "insufficient"

        llm_conf = max(0, min(100, int(data.get("confidence", 50))))
        correction = data.get("correction") or None
        if llm_verdict in {"verified", "insufficient"}:
            correction = None

        # Step 7: blend LLM verdict + NLI signal into final confidence
        final_verdict, final_conf = _blend_confidence(
            llm_verdict, llm_conf, nli_label, nli_score_val
        )

        return ClaimResult(
            claim=claim,
            verdict=final_verdict,
            confidence=final_conf,
            evidence_summary=data.get("evidence_summary", ""),
            source=contexts[0].get("source", "Unknown") if contexts else "System",
            correction=correction,
            evidence_urls=evidence_urls,
            primary_source_url=evidence_urls[0] if evidence_urls else None,
            llm_reasoning=(data.get("reasoning") or data.get("evidence_summary") or "").strip() or None,
            nli_label=nli_label,
            nli_score=round(nli_score_val, 4),
        )
    except Exception as exc:
        logger.warning("LLM judge fallback for claim due to %s: %s", type(exc).__name__, exc)
        result = _heuristic_judge_claim(claim, contexts, evidence_urls)
        # Attach NLI even in fallback path
        result.nli_label = nli_label
        result.nli_score = round(nli_score_val, 4)
        return result


# ═══════════════════════════════════════════════════════════════
# Stage 5: Topic relevance (global + per-segment)
# ═══════════════════════════════════════════════════════════════

def evaluate_topic_relevance(claims: List[str], topic: str, text: str = "") -> float:
    """Return relevance score 0-1."""
    if not claims and not text:
        return 0.0

    # When we have enough claims, evaluate claims against topic.
    # When claims are few/empty (e.g. personal topics where most were filtered),
    # evaluate the raw transcript text against the topic instead.
    if len(claims) >= 2:
        sample = claims[:10]
        block = "\n".join(f"- {c}" for c in sample)
        sys_prompt = (
            "Evaluate what fraction of claims are relevant to the topic.\n"
            'Return JSON: {"relevance_score": 0-100}'
        )
        usr_prompt = f"TOPIC: {topic}\nCLAIMS:\n{block}"
    else:
        transcript_sample = (text or "").strip()[:2000]
        if not transcript_sample:
            return _fallback_topic_relevance(claims, topic, text)
        sys_prompt = (
            "Rate how relevant the transcript content is to the declared topic.\n"
            "100 = entirely about the topic, 0 = completely unrelated.\n"
            'Return JSON: {"relevance_score": 0-100}'
        )
        usr_prompt = f"TOPIC: {topic}\nTRANSCRIPT:\n{transcript_sample}"

    try:
        data = _invoke_and_parse_json(sys_prompt, usr_prompt, "topic_relevance")
        raw_score = data.get("relevance_score")
        if raw_score is None:
            raise ValueError("Missing relevance_score from LLM response")
        return max(0.0, min(1.0, float(raw_score) / 100))
    except Exception:
        return _fallback_topic_relevance(claims, topic, text)


def detect_off_topic_segments(text: str, topic: str) -> List[OffTopicSegment]:
    """Split text into ~paragraph chunks and flag those that drift from the topic."""
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
    if not paragraphs:
        return []

    block = "\n---\n".join(f"[{i}] {p[:300]}" for i, p in enumerate(paragraphs))
    sys = (
        "For each numbered paragraph, score its relevance to the topic on 0-1 scale.\n"
        'Return JSON array: [{"index": 0, "score": 0.9}, ...]'
    )
    usr = f"TOPIC: {topic}\n\nPARAGRAPHS:\n{block}"
    try:
        scores = _invoke_and_parse_json(sys, usr, "off_topic_segments")
    except Exception:
        return []

    segments: List[OffTopicSegment] = []
    char_offset = 0
    for entry in scores:
        idx = int(entry.get("index", -1))
        score = float(entry.get("score", 1.0))
        if 0 <= idx < len(paragraphs) and score < config.TOPIC_MEDIUM_THRESHOLD:
            para = paragraphs[idx]
            start = text.find(para, char_offset)
            if start == -1:
                start = char_offset
            segments.append(OffTopicSegment(
                text=para[:200],
                start=float(start),
                end=float(start + len(para)),
                score=round(score, 4),
            ))
    return segments


# ═══════════════════════════════════════════════════════════════
# Public entry point
# ═══════════════════════════════════════════════════════════════

def score(full_text: str, declared_topic: str) -> ContentRelevanceResult:
    """
    Run the full 8-step content-relevance pipeline (synchronous).

    Pipeline
    --------
    Step 1  Input                   – received as arguments
    Step 2  Claim Extraction        – extract_claims()
    Step 3  Claim Normalization     – _normalize_claims() [inside extract_claims]
    Step 4  Multi-Source Retrieval  – gather_evidence() (web + Wikipedia)
    Step 5  Evidence Reranking      – _rerank_evidence() per claim
    Step 6  Claim Verification      – NLI (_nli_check) + LLM (_judge_claim)
    Step 7  Confidence Scoring      – _blend_confidence() [inside _judge_claim]
    Step 8  Aggregation             – factual_accuracy + topic_relevance

    Parameters
    ----------
    full_text : str
        Raw transcript text.
    declared_topic : str
        The topic the speaker claimed to be discussing.

    Returns
    -------
    ContentRelevanceResult
        Structured result ready for DB storage or API serialisation.
    """
    # ── Step 2 + 3: Extract and normalize claims ─────────────────────────
    cleaned_text, claims = extract_claims(full_text, declared_topic)
    logger.info("Pipeline: %d normalized claims extracted", len(claims))

    # ── Step 4: Multi-source retrieval (web + Wikipedia) ─────────────────
    evidence_docs = gather_evidence(claims, declared_topic)
    logger.info("Pipeline: %d evidence documents gathered", len(evidence_docs))

    # ── Step 4b: Build FAISS index for initial candidate retrieval ────────
    faiss_store = _build_faiss(evidence_docs)

    # ── Pre-compute evidence quality label used by LLM judge ─────────────
    _, quality_level = score_evidence_quality(evidence_docs)
    logger.info("Pipeline: evidence quality level = %s", quality_level)

    # ── Steps 5–7: Per-claim: rerank → NLI check → hybrid judge ──────────
    claim_results: List[ClaimResult] = []
    for claim in claims:
        # Step 5: FAISS candidate retrieval, then cross-encoder rerank
        candidates = _vector_search(faiss_store, claim, k=max(config.RERANKER_TOP_K * 2, 6))
        reranked_contexts = _rerank_evidence(claim, candidates)

        # Step 6: NLI check against combined evidence text
        combined_evidence = " ".join(
            (d.get("content") or "")[:300] for d in reranked_contexts
        )
        nli_result = _nli_check(claim, combined_evidence)

        # Step 6+7: LLM judge + confidence blending
        cr = _judge_claim(claim, reranked_contexts, declared_topic, quality_level, nli_result)
        claim_results.append(cr)

    # ── Step 8a: Aggregate factual accuracy ──────────────────────────────
    if claim_results:
        verdict_weight = {
            "verified": 1.0,
            "partially_true": 0.5,
            "insufficient": 0.25,
            "hallucinated": 0.0,
        }
        factual_accuracy = sum(verdict_weight.get(c.verdict, 0.0) for c in claim_results) / len(claim_results)
    else:
        factual_accuracy = 0.0

    # ── Step 8b: Topic relevance (global score; off-topic segments disabled) ─
    # Use the full cleaned transcript for topic relevance, not just surviving
    # fact-checkable claims — personal topics may have few verifiable claims
    # but the transcript is still on-topic.
    topic_match_score = evaluate_topic_relevance(claims, declared_topic, full_text)
    off_topic: List[OffTopicSegment] = []  # Disabled per user preference

    # ── Step 8c: Label ────────────────────────────────────────────────────
    if topic_match_score >= config.TOPIC_HIGH_THRESHOLD:
        label = "High"
    elif topic_match_score >= config.TOPIC_MEDIUM_THRESHOLD:
        label = "Medium"
    else:
        label = "Low"

    # ── Step 8d: Evidence snippets (top supporting quotes) ────────────────
    evidence_snippets = [
        cr.evidence_summary
        for cr in claim_results
        if cr.verdict in {"verified", "partially_true"} and cr.evidence_summary
    ][:5]

    # ── Step 8e: Overall score ─────────────────────────────────────────────
    # When claims exist: 40% topic + 60% factual.
    # When no claims were extracted: 100% topic (don't penalize for absence of facts).
    if claim_results:
        overall = int(round(topic_match_score * 40 + factual_accuracy * 60))
    else:
        overall = int(round(topic_match_score * 100))
    overall = max(0, min(100, overall))

    logger.info(
        "Pipeline complete: topic_match=%.2f (%s), factual=%.2f, overall=%d",
        topic_match_score, label, factual_accuracy, overall,
    )

    return ContentRelevanceResult(
        topic_match_score=round(topic_match_score, 4),
        topic_match_label=label,
        off_topic_segments=off_topic,
        factual_accuracy=round(factual_accuracy, 4),
        evidence_snippets=evidence_snippets,
        overall_content_score=overall,
        claim_results=claim_results,
    )
