from celery import Celery
from app.core.config import settings
from app.core.logging import setup_logger

logger = setup_logger()
logger.info("⚙️ Initializing Celery worker")

celery_app = Celery(
    "review_agent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.task_routes = {
    "app.tasks.analyzer.*": {"queue": "analyzer"}
}


from app.tasks import analyzer  

logger.info("⚙️ Celery worker initialized and tasks registered")
