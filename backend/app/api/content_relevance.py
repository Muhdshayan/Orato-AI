"""
Content Relevance – FastAPI Router
=====================================
GET  /api/v1/content-relevance/{transcript_id}
GET  /api/v1/content-relevance/submission/{submission_id}
POST /api/v1/content-relevance/submission/{submission_id}/analyze

Requires Bearer-token auth via ``Depends(get_current_user)``
(same pattern as ``app.api.video``).

Register in ``backend/main.py``::

    from app.api.content_relevance import router as content_relevance_router
    app.include_router(
        content_relevance_router,
        prefix="/api/v1/content-relevance",
        tags=["Content Relevance"],
    )
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.users import get_current_user
from app.core.database import execute_query
from python_modules.content_relevance.content_relevance_service import (
    content_relevance_service,
)

router = APIRouter()


def _find_content_relevance_for_submission(submission_id: str):
    """
    Find content relevance data for ANY transcript belonging to the submission.
    Returns the result dict or None.
    """
    rows = execute_query(
        """
        SELECT t.transcript_id
        FROM transcripts t
        JOIN content_relevance cr ON cr.transcript_id = t.transcript_id
        WHERE t.submission_id = %s
        ORDER BY cr.created_at DESC
        LIMIT 1
        """,
        (submission_id,),
    )
    if not rows:
        return None
    tid = rows[0][0] if isinstance(rows[0], (list, tuple)) else rows[0].get("transcript_id")
    return content_relevance_service.get_by_transcript(str(tid))


# ── GET by submission (preferred by frontend) ────────────────────────

@router.get("/submission/{submission_id}")
def get_content_relevance_by_submission(
    submission_id: str,
    _current_user=Depends(get_current_user),
):
    """Return content-relevance for a submission (searches all its transcripts)."""
    print(f"🔍 Content-Relevance API: Looking for submission_id={submission_id}")
    result = _find_content_relevance_for_submission(submission_id)
    if result is not None:
        print(f"✅ Found content relevance for submission {submission_id}")
        return result
    raise HTTPException(status_code=404, detail="Content relevance not yet analyzed for this submission")


# ── POST trigger on-demand analysis ──────────────────────────────────

@router.post("/submission/{submission_id}/analyze")
def trigger_content_relevance(
    submission_id: str,
    force: bool = Query(False, description="Recompute and store a fresh content-relevance row"),
    _current_user=Depends(get_current_user),
):
    """
    Run content-relevance analysis on-demand for a submission.
    Finds the latest transcript and runs the scorer.
    """
    print(f"🚀 Content-Relevance API: Triggering analysis for submission_id={submission_id}")

    # Already analysed?
    existing = _find_content_relevance_for_submission(submission_id)
    if existing is not None and not force:
        print(f"✅ Already analysed – returning cached result")
        return {"status": "completed", "result": existing}
    if existing is not None and force:
        print("🔁 Force=true supplied - recomputing content relevance")

    # Find latest transcript
    rows = execute_query(
        """
        SELECT transcript_id, text FROM transcripts
        WHERE submission_id = %s
        ORDER BY created_at DESC LIMIT 1
        """,
        (submission_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No transcript found for this submission")

    row = rows[0]
    transcript_id = str(row[0] if isinstance(row, (list, tuple)) else row.get("transcript_id"))
    full_text = row[1] if isinstance(row, (list, tuple)) else row.get("text", "")

    # Get declared topic
    topic_rows = execute_query(
        "SELECT declared_topic FROM video_submissions WHERE submission_id = %s",
        (submission_id,),
    )
    declared_topic = "General"
    if topic_rows:
        r = topic_rows[0]
        declared_topic = r[0] if isinstance(r, (list, tuple)) else r.get("declared_topic", "General")

    print(f"   transcript_id={transcript_id}, topic={declared_topic!r}, text_len={len(full_text)}")

    try:
        result = content_relevance_service.analyze_and_store(transcript_id, full_text, declared_topic)
        print(f"✅ Content-relevance analysis done and stored")
        return {"status": "completed", "result": result}
    except Exception as e:
        print(f"❌ Content-relevance analysis failed: {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# ── GET by transcript_id (legacy / fallback) ─────────────────────────

@router.get("/{transcript_id}")
def get_content_relevance(
    transcript_id: str,
    _current_user=Depends(get_current_user),
):
    """
    Return the content-relevance analysis for a given transcript.
    Falls back to searching ALL transcripts for the same submission.
    """
    print(f"🔍 Content-Relevance API: Looking for transcript_id={transcript_id}")

    # Direct match
    result = content_relevance_service.get_by_transcript(transcript_id)
    if result is not None:
        print(f"✅ Found content relevance for transcript_id={transcript_id}")
        return result

    print(f"⚠️ No direct match, searching submission-wide...")

    # Find submission for this transcript, then search all its transcripts
    try:
        rows = execute_query(
            "SELECT submission_id FROM transcripts WHERE transcript_id = %s LIMIT 1",
            (transcript_id,),
        )
        if not rows:
            raise HTTPException(status_code=404, detail=f"Transcript {transcript_id} not found")

        submission_id = str(rows[0][0] if isinstance(rows[0], (list, tuple)) else rows[0].get("submission_id"))
        result = _find_content_relevance_for_submission(submission_id)
        if result is not None:
            print(f"✅ Found content relevance via submission {submission_id}")
            return result

        raise HTTPException(
            status_code=404,
            detail="Content relevance not yet analyzed for this submission",
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERROR in content-relevance endpoint: {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {type(e).__name__}: {str(e)}")
