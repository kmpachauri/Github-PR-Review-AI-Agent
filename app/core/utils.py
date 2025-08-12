import redis
import json
from app.core.config import settings
from celery.result import AsyncResult
from app.tasks.worker import celery_app
from app.core.logging import setup_logger
logger = setup_logger()


redis_client = redis.Redis.from_url(settings.REDIS_URL)

def get_task_status(task_id: str) -> str:
    result = AsyncResult(task_id, app=celery_app)
    return result.status.lower()

def get_task_result(task_id: str):
    result = redis_client.get(task_id)
    if result:
        return json.loads(result)
    return None

def save_result(task_id: str, data: dict):
    redis_client.set(task_id, json.dumps(data), ex=3600)
    logger.info("💾 Saving result to Redis", extra={"task_id": task_id})

