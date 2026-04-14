from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("fastapi_production_starter")
celery_app.conf.broker_url = settings.CELERY_BROKER_URL
celery_app.conf.result_backend = settings.CELERY_RESULT_BACKEND
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.beat_schedule = {
    "cleanup-revoked-tokens-daily": {
        "task": "tasks.cleanup_revoked_tokens",
        "schedule": 60 * 60 * 24,
    }
}
celery_app.autodiscover_tasks(["app.tasks"])
