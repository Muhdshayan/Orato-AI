"""
Content Relevance – Standalone Test Script
==========================================
Run content relevance analysis on transcript + topic without starting the
full backend (no CV, no transcription). Fast iteration for testing.

Usage:
    python test_content_relevance.py
    python test_content_relevance.py "Your transcript here" "Your topic"
    python test_content_relevance.py --file transcript.txt --topic Pakistan

Run from project root with venv activated.
"""
import os
import sys

# Must be set before any content_relevance import (avoids app/database)
os.environ["CR_STANDALONE"] = "1"

import argparse
import json

# ── 1. Load env from backend/config.env ─────────────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
_ENV_FILE = os.path.join(_ROOT, "backend", "config.env")
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip()
                if len(val) >= 2 and val[0] in '"\'' and val[-1] == val[0]:
                    val = val[1:-1]
                os.environ.setdefault(key, val)
    print(f"[env] Loaded {_ENV_FILE}\n")
else:
    print(f"[warn] {_ENV_FILE} not found - using system env\n")

# ── 2. Ensure project root is on path ───────────────────────────────────────
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── 3. Import scorer (CR_STANDALONE=1 skips service/database) ─────────────────
from python_modules.content_relevance.scorer import score

# Default transcript + topic for quick testing
DEFAULT_TRANSCRIPT = (
    "Asalaakum, my name is Mamad Shayan Neyman. Today the topic is Pakistan. "
    "Pakistan was founded in nineteen fifty. Pakistan has ten provinces, which are "
    "Sindh, Balochistan, Hyderabad, Karathi, Lake Vivak. Pakistan founder was "
    "Narendra Modi and Pakistan has uh a lot of rivers. Uh Chalam is one of the "
    "rivers in Pakistan."
)
DEFAULT_TOPIC = "Pakistan"


def main():
    parser = argparse.ArgumentParser(
        description="Run content relevance analysis on transcript + topic"
    )
    parser.add_argument(
        "transcript",
        nargs="?",
        default=DEFAULT_TRANSCRIPT,
        help="Transcript text (or use --file)",
    )
    parser.add_argument(
        "topic",
        nargs="?",
        default=DEFAULT_TOPIC,
        help="Declared topic (default: Pakistan)",
    )
    parser.add_argument(
        "--file", "-f",
        help="Read transcript from file instead of argument",
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output full result as JSON",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress INFO logs (only show result)",
    )
    args = parser.parse_args()

    transcript = args.transcript
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            transcript = f.read()

    topic = args.topic

    if args.quiet:
        import logging
        logging.getLogger("content_relevance").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

    print("=" * 60)
    print("Content Relevance – Test Run")
    print("=" * 60)
    print(f"Topic: {topic}")
    print(f"Transcript length: {len(transcript)} chars")
    print("-" * 60)

    result = score(transcript, topic)

    if args.json:
        print(json.dumps(result.to_api_dict(), indent=2))
        return

    # Human-readable summary
    api = result.to_api_dict()
    print(f"\nOverall Score: {api['overall_content_score']}")
    print(f"Topic Match:  {api['topic_match_score']*100:.0f}% ({api['topic_match_label']})")
    print(f"Factual:      {api['factual_accuracy']*100:.0f}%")
    print(f"Claims:       {len(api['claim_results'])}")
    print()

    for i, cr in enumerate(api["claim_results"], 1):
        verdict = cr["verdict"].upper()
        conf = cr.get("confidence", 0)
        print(f"  {i}. {cr['claim']}")
        print(f"     Verdict: {verdict} ({conf}%)")
        if cr.get("llm_reasoning"):
            r = cr["llm_reasoning"]
            print(f"     Reasoning: {r[:150]}{'...' if len(r) > 150 else ''}")
        if cr.get("evidence_urls"):
            print(f"     Sources: {cr['evidence_urls'][:2]}")
        print()

    if api.get("evidence_snippets"):
        print("Key Evidence Snippets:")
        for s in api["evidence_snippets"][:3]:
            print(f"  - {s[:100]}...")
    print("=" * 60)


if __name__ == "__main__":
    main()
