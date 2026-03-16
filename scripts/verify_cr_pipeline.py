"""
Content Relevance Pipeline – Verification Script
=================================================
Run from the project root:

    python verify_cr_pipeline.py

Checks every component of the 8-step pipeline and prints a clear PASS / FAIL
table so you know exactly what is working before running a live analysis.
"""

import os
import sys
import time

# ── 1. Load env vars from backend/config.env ─────────────────────────────────
_ENV_FILE = os.path.join(os.path.dirname(__file__), "backend", "config.env")
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())
    print(f"[env]  Loaded {_ENV_FILE}\n")
else:
    print(f"[warn] config.env not found at {_ENV_FILE} - relying on system env\n")

# ── 2. Add project root to sys.path so python_modules imports work ────────────
_ROOT = os.path.dirname(__file__)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── Helpers ───────────────────────────────────────────────────────────────────

GREEN  = ""
RED    = ""
YELLOW = ""
RESET  = ""
BOLD   = ""

results: list[tuple[str, str, str]] = []   # (component, status, detail)


def _pass(component: str, detail: str = "") -> None:
    results.append((component, "PASS", detail))
    print(f"  [PASS]  {component}" + (f"  -- {detail}" if detail else ""))


def _fail(component: str, detail: str = "") -> None:
    results.append((component, "FAIL", detail))
    print(f"  [FAIL]  {component}" + (f"  -- {detail}" if detail else ""))


def _warn(component: str, detail: str = "") -> None:
    results.append((component, "WARN", detail))
    print(f"  [WARN]  {component}" + (f"  -- {detail}" if detail else ""))


def _section(title: str) -> None:
    print(f"\n" + "-"*60)
    print(f"  {title}")
    print("-"*60)


# ═════════════════════════════════════════════════════════════════════════════
# CHECK 1 - Config / env-var loading
# ═════════════════════════════════════════════════════════════════════════════
_section("1 · Config & Environment Variables")
try:
    # Import config directly (bypass __init__.py which pulls in app.core.database)
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "cr_config",
        os.path.join(_ROOT, "python_modules", "content_relevance", "config.py"),
    )
    cr_config = _ilu.module_from_spec(_spec)  # type: ignore
    _spec.loader.exec_module(cr_config)  # type: ignore

    # Show key values (mask secrets)
    def _mask(s: str) -> str:
        if not s:
            return "(empty)"
        return s[:6] + "..." + s[-4:] if len(s) > 12 else s[:3] + "..."

    print(f"       LLM_PROVIDER      = {cr_config.LLM_PROVIDER}")
    print(f"       GROQ_MODEL        = {cr_config.GROQ_MODEL}")
    print(f"       GROQ_API_KEY      = {_mask(cr_config.GROQ_API_KEY)}")
    print(f"       TAVILY_API_KEY    = {_mask(cr_config.TAVILY_API_KEY)}")
    print(f"       EMBEDDING_MODEL   = {cr_config.EMBEDDING_MODEL}")
    print(f"       NLI_MODEL         = {cr_config.NLI_MODEL}")
    print(f"       RERANKER_MODEL    = {cr_config.RERANKER_MODEL}")
    print(f"       WIKIPEDIA_MAX     = {cr_config.WIKIPEDIA_MAX_RESULTS}")

    if not cr_config.GROQ_API_KEY and cr_config.LLM_PROVIDER == "groq":
        _warn("Config", "GROQ_API_KEY is empty - LLM calls will fail")
    elif not cr_config.OPENAI_API_KEY and cr_config.LLM_PROVIDER == "openai":
        _warn("Config", "OPENAI_API_KEY is empty - LLM calls will fail")
    else:
        _pass("Config", "All keys present")

    if not cr_config.TAVILY_API_KEY:
        _warn("Config / Tavily key", "TAVILY_API_KEY empty - will fall back to DuckDuckGo")
    else:
        _pass("Config / Tavily key")

except Exception as e:
    _fail("Config", str(e))
    cr_config = None  # type: ignore


# ═════════════════════════════════════════════════════════════════════════════
# CHECK 2 - LLM  (Groq or OpenAI)
# ═════════════════════════════════════════════════════════════════════════════
_section("2 · LLM API  (Step 2: claim extraction)")
try:
    if cr_config and cr_config.LLM_PROVIDER == "groq":
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage
        llm = ChatGroq(
            model=cr_config.GROQ_MODEL,
            api_key=cr_config.GROQ_API_KEY,
            temperature=0,
        )
        t0 = time.time()
        resp = llm.invoke([HumanMessage(content='Reply with exactly: {"ok": true}')])
        elapsed = round(time.time() - t0, 2)
        _pass("Groq LLM", f"model={cr_config.GROQ_MODEL}  latency={elapsed}s  reply={resp.content[:60]!r}")
    elif cr_config:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        llm = ChatOpenAI(model=cr_config.OPENAI_MODEL, api_key=cr_config.OPENAI_API_KEY, temperature=0)
        t0 = time.time()
        resp = llm.invoke([HumanMessage(content='Reply with exactly: {"ok": true}')])
        elapsed = round(time.time() - t0, 2)
        _pass("OpenAI LLM", f"model={cr_config.OPENAI_MODEL}  latency={elapsed}s")
except Exception as e:
    _fail("LLM API", str(e))


# ═════════════════════════════════════════════════════════════════════════════
# CHECK 3 - Embedding model  (sentence-transformers)
# ═════════════════════════════════════════════════════════════════════════════
_section("3 · Embedding Model  (Step 5: FAISS index)")
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    model_name = cr_config.EMBEDDING_MODEL if cr_config else "sentence-transformers/all-MiniLM-L6-v2"
    t0 = time.time()
    emb = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    vec = emb.embed_query("test sentence for verification")
    elapsed = round(time.time() - t0, 2)
    _pass("Embeddings", f"model={model_name}  dim={len(vec)}  load+encode={elapsed}s")
except Exception as e:
    _fail("Embeddings", str(e))


# ═════════════════════════════════════════════════════════════════════════════
# CHECK 4 - Tavily web search  (Step 4: retrieval channel 1)
# ═════════════════════════════════════════════════════════════════════════════
_section("4 · Tavily Web Search  (Step 4: retrieval)")
_tavily_key = (cr_config.TAVILY_API_KEY if cr_config else None) or os.getenv("TAVILY_API_KEY", "")
if _tavily_key:
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=_tavily_key)
        t0 = time.time()
        resp = client.search(query="Pakistan independence year", search_depth="basic", max_results=2)
        elapsed = round(time.time() - t0, 2)
        n = len(resp.get("results", []))
        _pass("Tavily Search", f"{n} results returned  latency={elapsed}s")
    except Exception as e:
        _fail("Tavily Search", str(e))
else:
    _warn("Tavily Search", "Skipped - no API key (DuckDuckGo fallback will be used)")


# ═════════════════════════════════════════════════════════════════════════════
# CHECK 5 - DuckDuckGo fallback  (Step 4: retrieval channel 1 fallback)
# ═════════════════════════════════════════════════════════════════════════════
_section("5 · DuckDuckGo Search  (Step 4: fallback retrieval)")
try:
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS
    t0 = time.time()
    with DDGS() as ddgs:
        try:
            results_ddg = list(ddgs.text("Pakistan independence year", max_results=2, backend="lite"))
        except TypeError:
            results_ddg = list(ddgs.text("Pakistan independence year", max_results=2))
    elapsed = round(time.time() - t0, 2)
    _pass("DuckDuckGo Search", f"{len(results_ddg)} results  latency={elapsed}s")
except Exception as e:
    _fail("DuckDuckGo Search", str(e))


# ═════════════════════════════════════════════════════════════════════════════
# CHECK 6 - Wikipedia API  (Step 4: retrieval channel 2)
# ═════════════════════════════════════════════════════════════════════════════
_section("6 · Wikipedia API  (Step 4: dedicated retrieval)")
try:
    import json
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    timeout = cr_config.WIKIPEDIA_TIMEOUT_SECONDS if cr_config else 6.0
    params = urlencode({
        "action": "query",
        "list": "search",
        "srsearch": "Pakistan",
        "srlimit": 2,
        "format": "json",
    })
    url = f"https://en.wikipedia.org/w/api.php?{params}"
    req = Request(url, headers={"User-Agent": "OratoAI-Verify/1.0"})
    t0 = time.time()
    with urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    elapsed = round(time.time() - t0, 2)
    hits = data.get("query", {}).get("search", [])
    titles = [h["title"] for h in hits]
    _pass("Wikipedia API", f"{len(hits)} results: {titles}  latency={elapsed}s")
except Exception as e:
    _fail("Wikipedia API", str(e))


# ═════════════════════════════════════════════════════════════════════════════
# CHECK 7 - Cross-encoder Reranker  (Step 5: evidence reranking)
# ═════════════════════════════════════════════════════════════════════════════
_section("7 · Cross-Encoder Reranker  (Step 5: evidence reranking)")
try:
    from sentence_transformers import CrossEncoder
    model_name = cr_config.RERANKER_MODEL if cr_config else "cross-encoder/ms-marco-MiniLM-L-6-v2"
    t0 = time.time()
    reranker = CrossEncoder(model_name, max_length=512)
    scores = reranker.predict([
        ("Pakistan founded in 1947", "Pakistan gained independence on 14 August 1947."),
        ("Pakistan founded in 1947", "The capital of France is Paris."),
    ])
    elapsed = round(time.time() - t0, 2)
    _pass(
        "Reranker",
        f"model={model_name}  "
        f"score[relevant]={scores[0]:.3f}  score[irrelevant]={scores[1]:.3f}  "
        f"load+predict={elapsed}s"
    )
    if scores[0] <= scores[1]:
        _warn("Reranker sanity", "Relevant doc scored <= irrelevant doc - model may not be loaded correctly")
except Exception as e:
    _fail("Reranker", str(e))


# ═════════════════════════════════════════════════════════════════════════════
# CHECK 8 - NLI Pipeline  (Step 6: entailment check)
# ═════════════════════════════════════════════════════════════════════════════
_section("8 · NLI Entailment Pipeline  (Step 6: claim verification)")
try:
    from transformers import pipeline as hf_pipeline
    model_name = cr_config.NLI_MODEL if cr_config else "cross-encoder/nli-deberta-v3-small"
    t0 = time.time()
    nli = hf_pipeline("zero-shot-classification", model=model_name, device=-1)
    candidate_labels = ["entailment", "neutral", "contradiction"]
    # Test 1: evidence should entail the claim
    r1 = nli(
        "Premise: Pakistan gained independence on 14 August 1947.\nHypothesis: Pakistan was founded in 1947.",
        candidate_labels,
        hypothesis_template="{}",
        multi_label=False,
    )
    # Test 2: evidence should contradict the claim
    r2 = nli(
        "Premise: Pakistan gained independence on 14 August 1947.\nHypothesis: Pakistan was founded in 2005.",
        candidate_labels,
        hypothesis_template="{}",
        multi_label=False,
    )
    elapsed = round(time.time() - t0, 2)
    label1 = r1["labels"][0]
    label2 = r2["labels"][0]
    score1 = r1["scores"][0]
    score2 = r2["scores"][0]
    _pass(
        "NLI Pipeline",
        f"model={model_name}  "
        f"correct->{label1}({score1:.2f})  "
        f"wrong->{label2}({score2:.2f})  "
        f"load+infer={elapsed}s"
    )
    if label1 != "entailment":
        _warn("NLI sanity (test 1)", f"Expected 'entailment' but got '{label1}'")
    if label2 != "contradiction":
        _warn("NLI sanity (test 2)", f"Expected 'contradiction' but got '{label2}'")
except Exception as e:
    _fail("NLI Pipeline", str(e))


# ═════════════════════════════════════════════════════════════════════════════
# SUMMARY TABLE
# ═════════════════════════════════════════════════════════════════════════════
print("\n\n" + "="*60)
print("  VERIFICATION SUMMARY")
print("="*60)

col_w = 38
passed = sum(1 for _, s, _ in results if s == "PASS")
failed = sum(1 for _, s, _ in results if s == "FAIL")
warned = sum(1 for _, s, _ in results if s == "WARN")

for comp, status, detail in results:
    tag = f"[{status}]"
    detail_short = detail[:55] + "..." if len(detail) > 55 else detail
    print(f"  {tag:<7}  {comp:<{col_w}}  {detail_short}")

print("-"*60)
print(f"  Total: {passed} PASS  |  {failed} FAIL  |  {warned} WARN")
print("="*60 + "\n")

if failed > 0:
    sys.exit(1)
