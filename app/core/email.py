import logging
from pathlib import Path
from typing import Any

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _mail_config() -> ConnectionConfig:
    settings = get_settings()
    return ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
        TEMPLATE_FOLDER=Path("app/templates/email"),
    )


async def send_email(
    to: str,
    subject: str,
    template_name: str,
    context: dict[str, Any],
) -> None:
    settings = get_settings()
    if not settings.MAIL_ENABLED:
        logger.info("MAIL_DISABLED to=%s subject=%s template=%s", to, subject, template_name)
        return

    fm = FastMail(_mail_config())
    message = MessageSchema(
        subject=subject,
        recipients=[to],
        template_body=context,
        subtype=MessageType.html,
    )
    await fm.send_message(message, template_name=template_name)
