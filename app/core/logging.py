import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

# Patterns applied by PIIRedactionFilter when LOG_PII_REDACT=true.
_PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "[email]"),
    # Credit card numbers (4 groups of 4 digits with separators)
    (re.compile(r"\b(?:\d[ -]?){13,15}\d\b"), "[card]"),
    # US phone numbers
    (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[phone]"),
    # SSN (XXX-XX-XXXX)
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[ssn]"),
]


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get("-")
        return True


class PIIRedactionFilter(logging.Filter):
    """Redacts common PII patterns from log messages. Enable via LOG_PII_REDACT=true."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact(str(record.msg))
        record.args = tuple(_redact(str(a)) if isinstance(a, str) else a for a in record.args or ())
        return True


def _redact(text: str) -> str:
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _get_trace_context() -> tuple[str, str]:
    """Return (trace_id, span_id) strings from the active OTel span, or ('-', '-')."""
    try:
        from opentelemetry import trace as otel_trace

        span = otel_trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.is_valid:
            return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")
    except Exception:
        pass
    return "-", "-"


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        trace_id, span_id = _get_trace_context()
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "trace_id": trace_id,
            "span_id": span_id,
        }
        return json.dumps(payload)


def setup_logging(
    *, debug: bool = False, log_format: str = "text", pii_redact: bool = False
) -> None:
    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(request_id)s | %(message)s"

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    root_handler = logging.getLogger().handlers[0]
    root_handler.addFilter(RequestIDFilter())
    if pii_redact:
        root_handler.addFilter(PIIRedactionFilter())
    if log_format == "json":
        root_handler.setFormatter(JSONFormatter())

    # Quiet noisy third-party loggers in non-debug mode
    if not debug:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
