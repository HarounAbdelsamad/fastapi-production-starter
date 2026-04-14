import asyncio
from typing import Any

from app.core.email import send_email
from app.worker import celery_app


@celery_app.task(name="tasks.send_email")
def send_email_task(to: str, subject: str, template_name: str, context: dict[str, Any]) -> None:
    asyncio.run(send_email(to=to, subject=subject, template_name=template_name, context=context))
