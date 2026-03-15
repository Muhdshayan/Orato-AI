I have a standalone content relevance project that I need to restructure so it can be 
dropped into an existing FastAPI + React application with zero friction. 
Below is the exact architecture of the host project. Rewrite/package my code to match it.

---

## HOST PROJECT ARCHITECTURE

### Backend: FastAPI (Python)
- Framework: FastAPI with async background tasks
- DB: PostgreSQL accessed via a thin `execute_query(sql, params)` helper
- File storage: MinIO (files already downloaded to tmp paths before being passed to services)
- Python path: the repo root is on sys.path, so imports like 
  `from python_modules.content_relevance.xxx import yyy` work directly

### The Analysis Pipeline (how new services plug in)
The orchestrator (`backend/app/services/analysis_orchestrator.py`) runs audio and video 
pipelines in parallel. The audio pipeline already:
  1. Calls `simple_asr_service.transcribe_audio(audio_path)` → returns `transcript_data` dict
  2. Calls `simple_asr_service.store_transcript(submission_id, transcript_data)` → returns `transcript_id` (UUID str)
  3. Calls `speech_metrics_service.analyze_and_store_metrics(transcript_id, transcript_data)`

Content relevance must run as a 4th step inside `_run_audio_pipeline`, right after step 3, 
called as:
  `content_relevance_service.analyze_and_store(transcript_id, full_text, declared_topic)`

`declared_topic` is fetched from DB by querying:
  `SELECT declared_topic FROM video_submissions WHERE submission_id = %s`

### Database schema for content relevance (already exists — do NOT recreate):
```sql
CREATE TABLE content_relevance (
    content_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_id UUID NOT NULL REFERENCES transcripts(transcript_id) ON DELETE CASCADE,
    topic_match_score  FLOAT,
    off_topic_segments JSONB,
    factual_accuracy   FLOAT,
    evidence_snippets  JSONB,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Existing services follow this exact pattern (use as the template):
```python
# python_modules/nlp_asr/speech_metrics_service.py
from app.core.database import execute_query

class SpeechMetricsService:
    def analyze_and_store_metrics(self, transcript_id: str, transcript_data: dict) -> dict:
        # ... pure analysis logic ...
        execute_query("INSERT INTO speech_metrics (...) VALUES (...)", (...))
        return results

speech_metrics_service = SpeechMetricsService()   # singleton at module level
```

---

## WHAT I NEED DELIVERED

Rewrite my content relevance logic into **exactly this file structure**:

```
python_modules/
  content_relevance/
    __init__.py                    # exports content_relevance_service singleton
    content_relevance_service.py   # main service class (see interface below)
    models.py                      # pure dataclasses / typed dicts, no DB imports
    scorer.py                      # core NLP/LLM scoring logic, no DB, no FastAPI
    config.py                      # thresholds, model names, env vars (use os.getenv)

backend/app/api/
  content_relevance.py             # FastAPI router with one GET endpoint (see below)
```

### Service interface (content_relevance_service.py):
```python
from app.core.database import execute_query

class ContentRelevanceService:
    def analyze_and_store(
        self,
        transcript_id: str,   # UUID string
        full_text: str,        # raw transcript text
        declared_topic: str    # e.g. "Climate Change"
    ) -> dict:
        """
        1. Call scorer.py to produce scores (no DB here)
        2. INSERT into content_relevance table
        3. Return the result dict
        Must be safe to call from a background thread (no async).
        """

content_relevance_service = ContentRelevanceService()
```

### API endpoint (backend/app/api/content_relevance.py):
```python
# GET /api/v1/content-relevance/{transcript_id}
# Auth: requires Bearer token (copy the Depends(get_current_user) pattern from video.py)
# Returns JSON matching this shape (frontend will consume it):
{
  "topic_match_score": 0.87,          # 0-1 float
  "topic_match_label": "High",        # "High" | "Medium" | "Low"
  "off_topic_segments": [             # list of text snippets that diverged from topic
    {"text": "...", "start": 12.3, "end": 18.7, "score": 0.31}
  ],
  "factual_accuracy": 0.72,
  "evidence_snippets": ["..."],       # key supporting quotes
  "overall_content_score": 82         # 0-100 int, shown as headline KPI
}
```

The router must be registerable in `backend/main.py` with:
```python
from app.api.content_relevance import router as content_relevance_router
app.include_router(content_relevance_router, prefix="/api/v1/content-relevance", tags=["Content Relevance"])
```

### Orchestrator modification needed (backend/app/services/analysis_orchestrator.py):
Show me the updated `_run_audio_pipeline` method only — do not rewrite the whole file.

### Frontend (React) — one new component:
File: `frontend/src/components/ContentRelevanceDashboard.js`

Style rules (must match the existing dark UI):
- Use the same Card/KPI pattern as MetricsDashboard.js (dark glass cards, 
  `rgba(255,255,255,0.02)` background, `var(--primary)` accent color)
- Use `react-chartjs-2` (already installed) for any charts
- Fetch data with axios from `/api/v1/content-relevance/{transcriptId}` — 
  look up `transcriptId` by calling the existing `transcriptAPI.getBySubmission(submissionId)` 
  pattern from `frontend/src/services/api.js`
- Export a named `ContentRelevanceDashboard` component that accepts `{ submissionId }` as props

Also show me the one-line addition to `AnalysisResults.js` tabs array:
```js
// current tabs array is:
const tabs = [
  { id: 'visual',  label: 'Body Language',  icon: Eye },
  { id: 'speech',  label: 'Speech Patterns', icon: Mic },
  { id: 'transcript', label: 'Transcript',  icon: FileText },
];
// Add: { id: 'content', label: 'Content Relevance', icon: BookOpen }
// and the corresponding <ContentRelevanceDashboard submissionId={submissionId} /> 
// in the tab body switch
```

---

## CONSTRAINTS
- No new npm packages. No new pip packages unless absolutely unavoidable 
  (if one is needed, state it explicitly and show `pip install X` command).
- All DB access goes through `execute_query` — no ORM, no raw psycopg2 connections.
- The service must be synchronous (no async/await) because it runs inside 
  `asyncio.to_thread(...)` in the orchestrator.
- scorer.py must be independently testable with no FastAPI or DB imports.
- Use Python type hints throughout.
- Do not modify any existing files except the two spots shown 
  (analysis_orchestrator.py `_run_audio_pipeline` and AnalysisResults.js tabs).
