"""Background job queue abstraction.

The ``JobQueue`` protocol decouples callers from the underlying queue backend.
Default adapter: Celery (``CELERY_ENABLED=true``).
RQ adapter is a ready-to-fill template for teams that prefer its simplicity.

See ``docs/operations/background-jobs.md`` for choosing between backends.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class JobQueue(Protocol):
    """Minimal interface every job queue backend must satisfy."""

    def enqueue(self, task_name: str, *args: Any, **kwargs: Any) -> str:
        """Enqueue a named task immediately. Returns the job/task ID."""
        ...

    def enqueue_in(self, delay_seconds: int, task_name: str, *args: Any, **kwargs: Any) -> str:
        """Enqueue a named task after *delay_seconds*. Returns the job/task ID."""
        ...


class CeleryJobQueue:
    """Celery-backed adapter. Requires ``CELERY_ENABLED=true``."""

    def enqueue(self, task_name: str, *args: Any, **kwargs: Any) -> str:
        from app.worker import celery_app

        result = celery_app.send_task(task_name, args=args, kwargs=kwargs)
        return result.id

    def enqueue_in(self, delay_seconds: int, task_name: str, *args: Any, **kwargs: Any) -> str:
        from app.worker import celery_app

        result = celery_app.send_task(
            task_name, args=args, kwargs=kwargs, countdown=delay_seconds
        )
        return result.id


class RQJobQueue:
    """RQ adapter sketch.

    Install:  ``uv add rq``
    Activate: set ``JOB_QUEUE_BACKEND=rq`` and configure ``REDIS_URL``.

    This class is intentionally incomplete — it is a starting point for teams
    that prefer RQ's simplicity over Celery's feature set.  Implement the body
    of ``enqueue`` / ``enqueue_in`` once you add the ``rq`` dependency.
    """

    def __init__(self) -> None:
        try:
            import redis as sync_redis
            import rq

            from app.core.config import get_settings

            settings = get_settings()
            conn = sync_redis.from_url(settings.REDIS_URL)
            self._queue = rq.Queue(connection=conn)
        except ImportError as exc:
            raise RuntimeError("RQJobQueue requires 'rq': uv add rq") from exc

    def enqueue(self, task_name: str, *args: Any, **kwargs: Any) -> str:
        # RQ enqueues callables, not name strings — resolve the callable first.
        # Example: from app.tasks.email_tasks import send_email_task
        #          job = self._queue.enqueue(send_email_task, *args, **kwargs)
        raise NotImplementedError(
            "RQJobQueue.enqueue: resolve the callable from task_name, "
            "then call self._queue.enqueue(fn, *args, **kwargs)"
        )

    def enqueue_in(self, delay_seconds: int, task_name: str, *args: Any, **kwargs: Any) -> str:
        # from datetime import timedelta
        # job = self._queue.enqueue_in(timedelta(seconds=delay_seconds), fn, *args, **kwargs)
        raise NotImplementedError(
            "RQJobQueue.enqueue_in: use self._queue.enqueue_in(timedelta(...), fn, ...)"
        )


def get_job_queue() -> JobQueue:
    """Return the configured job queue backend.

    Raises ``RuntimeError`` when no backend is enabled.  Inject via
    ``Depends(get_job_queue)`` or call once per request context.
    """
    from app.core.config import get_settings

    settings = get_settings()
    if settings.CELERY_ENABLED:
        return CeleryJobQueue()
    raise RuntimeError(
        "No job queue backend enabled. "
        "Set CELERY_ENABLED=true (Celery) or JOB_QUEUE_BACKEND=rq (RQ)."
    )
