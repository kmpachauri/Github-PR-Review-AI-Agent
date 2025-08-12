from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from app.models.schemas import PRRequest
from app.tasks.analyzer import analyze_pull_request
from app.core.utils import get_task_status, get_task_result
from app.tasks.worker import celery_app
from celery.result import AsyncResult
from app.core.logging import setup_logger
logger = setup_logger()


router = APIRouter()

@router.post("/analyze-pr")
async def analyze_pr(request: PRRequest):
    try:
        logger.info("📩 Received /analyze-pr request", extra={"repo_url": request.repo_url, "pr_number": request.pr_number})
        
        task = analyze_pull_request.apply_async(
        args=[request.repo_url, request.pr_number, request.github_token],
        queue="code-review"
        )
        return {"task_id": task.id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}")
def get_status(task_id: str):
    logger.info("📊 Status check requested", extra={"task_id": task_id})
    status = get_task_status(task_id)
    return {"task_id": task_id, "status": status}


@router.get("/results/{task_id}")
def get_results(task_id: str):
    logger.info("📤 Results retrieval requested", extra={"task_id": task_id})
    result = get_task_result(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return result
