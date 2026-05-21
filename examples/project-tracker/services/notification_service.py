"""
Notification service — shows JobQueue protocol usage for background tasks.

Enqueues a Celery task (or any configured backend) without importing Celery
directly — callers are decoupled from the backend via the JobQueue protocol.
"""

from app.core.jobs import get_job_queue


def notify_assignee(task_id: int, assignee_id: int, message: str) -> str:
    """
    Enqueue a background job to notify the assignee.
    Returns the job ID string from the queue backend.
    """
    queue = get_job_queue()
    return queue.enqueue(
        "tasks.send_notification",
        task_id,
        assignee_id,
        message,
    )


def schedule_due_date_reminder(task_id: int, remind_seconds_before: int = 3600) -> str:
    """Enqueue a delayed reminder job `remind_seconds_before` seconds before due."""
    queue = get_job_queue()
    return queue.enqueue_in(
        remind_seconds_before,
        "tasks.send_due_date_reminder",
        task_id,
    )
