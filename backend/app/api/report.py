from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
from app.services.report_generator_service import report_generator_service
from app.core.database import execute_query
import json

router = APIRouter()

@router.get("/{submission_id}")
async def get_report(submission_id: str):
    """
    Retrieve the cumulative analysis report for a submission.
    """
    query = "SELECT * FROM analysis_reports WHERE submission_id = %s"
    result = execute_query(query, (submission_id,), fetch_one=True)
    
    if not result:
        # Check if analysis is still in progress
        job_query = "SELECT status FROM processing_jobs WHERE submission_id = %s"
        job = execute_query(job_query, (submission_id,), fetch_one=True)
        
        if job and job['status'] == 'PROCESSING':
            return {"status": "processing", "message": "Report is being generated"}
        
        raise HTTPException(status_code=404, detail="Report not found for this submission")

    # Parse JSON tips if stored as string
    tips = result['tips_json']
    if isinstance(tips, str):
        try:
            tips = json.loads(tips)
        except:
            pass

    return {
        "submission_id": result['submission_id'],
        "overall_score": result['overall_score'],
        "feedback": tips,
        "generated_at": result['generated_at'],
        "status": "completed"
    }

@router.post("/{submission_id}/generate")
async def generate_report_manual(submission_id: str, background_tasks: BackgroundTasks):
    """
    Manually trigger/re-trigger report generation.
    """
    # Simply trigger the service
    try:
        # We run it in a background task to return immediately 
        # but for this specific FYP context, a direct await is often preferred 
        # for debugging. We'll use direct await for now to confirm success.
        report = await report_generator_service.generate_report(submission_id)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
