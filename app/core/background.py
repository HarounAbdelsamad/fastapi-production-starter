from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import BackgroundTasks

from app.core.config import get_settings


def schedule_task(
    background_tasks: BackgroundTasks,
    func: Callable[..., Any] | Callable[..., Awaitable[Any]],
    *args: Any,
    **kwargs: Any,
) -> None:
    settings = get_settings()
    if settings.CELERY_ENABLED:
        # Celery-enabled paths should enqueue tasks inside caller services.
        return
    background_tasks.add_task(func, *args, **kwargs)
