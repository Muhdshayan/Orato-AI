"""
Content Relevance – Configuration
===================================
Thresholds, model names, and environment variables.
All settings read from env vars with sensible defaults.
"""

import os
from pathlib import Path
from typing import List

# Load env vars early so os.getenv(...) below can see keys such as GROQ_API_KEY.
# Source of truth is backend/config.env.
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
_PRIMARY_ENV_PATH = _REPO_ROOT / "backend" / "config.env"
_FALLBACK_ENV_CANDIDATES = [
    _REPO_ROOT / "config.env",
    Path.cwd() / "config.env",
]
ENV_SOURCE_PATH = ""


def _load_env_file(path: Path) -> None:
    """Minimal .env loader that does not require python-dotenv."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and (
            (value[0] == '"' and value[-1] == '"')
            or (value[0] == "'" and value[-1] == "'")
        ):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _apply_env(path: Path) -> None:
    global ENV_SOURCE_PATH
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(path, override=False)
    except Exception:
        pass
    _load_env_file(path)
    ENV_SOURCE_PATH = str(path)


if _PRIMARY_ENV_PATH.exists():
    _apply_env(_PRIMARY_ENV_PATH)
else:
    for _env_path in _FALLBACK_ENV_CANDIDATES:
        if _env_path.exists():
            _apply_env(_env_path)
            break

# ── LLM Provider ──────────────────────────────────────────────
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")  # "groq" | "openai"

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

# ── Search / Evidence Retrieval ───────────────────────────────
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
MAX_SEARCH_RESULTS: int = int(os.getenv("CR_MAX_SEARCH_RESULTS", "8"))
NUM_SEARCH_QUERIES: int = int(os.getenv("CR_NUM_SEARCH_QUERIES", "6"))
MAX_CLAIM_QUERIES: int = int(os.getenv("CR_MAX_CLAIM_QUERIES", "6"))
MAX_TOTAL_QUERIES: int = int(os.getenv("CR_MAX_TOTAL_QUERIES", "14"))

# ── Optional webpage scraping for fresher evidence ────────────
MAX_SCRAPED_PAGES: int = int(os.getenv("CR_MAX_SCRAPED_PAGES", "5"))
SCRAPE_TIMEOUT_SECONDS: float = float(os.getenv("CR_SCRAPE_TIMEOUT_SECONDS", "5"))
MAX_SCRAPED_CHARS: int = int(os.getenv("CR_MAX_SCRAPED_CHARS", "2200"))

# ── Embedding Model (local, free) ────────────────────────────
EMBEDDING_MODEL: str = os.getenv(
    "CR_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)

# ── NLI Model (local, free — Step 6: claim verification) ─────
NLI_MODEL: str = os.getenv("CR_NLI_MODEL", "cross-encoder/nli-deberta-v3-small")
NLI_ENTAILMENT_THRESHOLD: float = float(os.getenv("CR_NLI_ENTAIL_THRESH", "0.5"))

# ── Reranker Model (local, free — Step 5: evidence ranking) ──
RERANKER_MODEL: str = os.getenv("CR_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANKER_TOP_K: int = int(os.getenv("CR_RERANKER_TOP_K", "3"))

# ── Wikipedia Retrieval (Step 4: multi-source retrieval) ──────
WIKIPEDIA_MAX_RESULTS: int = int(os.getenv("CR_WIKI_MAX", "3"))
WIKIPEDIA_TIMEOUT_SECONDS: float = float(os.getenv("CR_WIKI_TIMEOUT", "6"))

# ── Scoring Thresholds ───────────────────────────────────────
TOPIC_HIGH_THRESHOLD: float = float(os.getenv("CR_TOPIC_HIGH", "0.70"))
TOPIC_MEDIUM_THRESHOLD: float = float(os.getenv("CR_TOPIC_MEDIUM", "0.40"))

EVIDENCE_QUALITY_THRESHOLD: float = float(
    os.getenv("CR_EVIDENCE_QUALITY_THRESHOLD", "0.4")
)
SIMILARITY_THRESHOLD: float = float(
    os.getenv("CR_SIMILARITY_THRESHOLD", "0.3")
)

# ── Text Processing ──────────────────────────────────────────
MAX_CLAIMS: int = int(os.getenv("CR_MAX_CLAIMS", "30"))
MAX_TEXT_CHARS: int = int(os.getenv("CR_MAX_TEXT_CHARS", "8000"))

# ── Authority domains for evidence quality scoring ───────────
AUTHORITY_DOMAINS: List[str] = [
    "wikipedia.org",
    "britannica.com",
    ".edu",
    ".gov",
    "bbc.com",
    "reuters.com",
    "ap.org",
    "aljazeera.com",
    "nytimes.com",
]

# ── Debugging ────────────────────────────────────────────────
LOG_LLM_FAILURES: bool = os.getenv("CR_LOG_LLM_FAILURES", "").lower() in {
    "1",
    "true",
    "yes",
    "y",
    "on",
}
