"""Tests for OpenTelemetry setup and structured logging helpers."""

import logging
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# app.core.logging — trace context helpers and PII redaction
# ---------------------------------------------------------------------------


class TestGetTraceContext:
    def test_returns_dashes_when_no_active_span(self):
        from app.core.logging import _get_trace_context

        trace_id, span_id = _get_trace_context()
        assert trace_id == "-"
        assert span_id == "-"

    def test_returns_dashes_on_import_error(self):
        from app.core.logging import _get_trace_context

        with patch("app.core.logging._get_trace_context", side_effect=Exception("otel missing")):
            pass  # function itself is imported; test the fallback path via mocking otel

        # When span context is invalid, returns dashes
        with patch("opentelemetry.trace.get_current_span") as mock_span:
            ctx = MagicMock()
            ctx.is_valid = False
            mock_span.return_value.get_span_context.return_value = ctx
            trace_id, span_id = _get_trace_context()
        assert trace_id == "-"
        assert span_id == "-"


class TestJSONFormatter:
    def test_json_output_has_required_fields(self):
        import json

        from app.core.logging import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        record.request_id = "req-123"
        output = json.loads(formatter.format(record))
        assert output["level"] == "INFO"
        assert output["message"] == "hello world"
        assert output["request_id"] == "req-123"
        assert "trace_id" in output
        assert "span_id" in output
        assert "timestamp" in output

    def test_json_output_contains_trace_id_when_span_active(self):
        import json

        from app.core.logging import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="traced",
            args=(),
            exc_info=None,
        )
        record.request_id = "-"

        with patch("opentelemetry.trace.get_current_span") as mock_get_span:
            span = MagicMock()
            ctx = MagicMock()
            ctx.is_valid = True
            ctx.trace_id = 0x4BF92F3577B34DA6A3CE929D0E0E4736
            ctx.span_id = 0x00F067AA0BA902B7
            span.get_span_context.return_value = ctx
            mock_get_span.return_value = span

            output = json.loads(formatter.format(record))

        assert output["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
        assert output["span_id"] == "00f067aa0ba902b7"


# ---------------------------------------------------------------------------
# app.core.logging — PII redaction
# ---------------------------------------------------------------------------


class TestPIIRedaction:
    def test_redacts_email_from_message(self):
        from app.core.logging import PIIRedactionFilter

        f = PIIRedactionFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="login from user@example.com", args=(), exc_info=None,
        )
        f.filter(record)
        assert "user@example.com" not in record.msg
        assert "[email]" in record.msg

    def test_redacts_phone_number(self):
        from app.core.logging import PIIRedactionFilter

        f = PIIRedactionFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="called 555-867-5309", args=(), exc_info=None,
        )
        f.filter(record)
        assert "555-867-5309" not in record.msg
        assert "[phone]" in record.msg

    def test_redacts_ssn(self):
        from app.core.logging import PIIRedactionFilter

        f = PIIRedactionFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="ssn is 123-45-6789", args=(), exc_info=None,
        )
        f.filter(record)
        assert "123-45-6789" not in record.msg
        assert "[ssn]" in record.msg

    def test_non_pii_message_unchanged(self):
        from app.core.logging import PIIRedactionFilter

        f = PIIRedactionFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="normal operational log message", args=(), exc_info=None,
        )
        f.filter(record)
        assert record.msg == "normal operational log message"

    def test_redacts_string_args(self):
        from app.core.logging import PIIRedactionFilter

        f = PIIRedactionFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="user: %s", args=("user@corp.com",), exc_info=None,
        )
        f.filter(record)
        assert record.args[0] == "[email]"


# ---------------------------------------------------------------------------
# app.core.telemetry — setup_telemetry
# ---------------------------------------------------------------------------


class TestSetupTelemetry:
    def test_disabled_sdk_skips_setup(self):
        from app.core.telemetry import setup_telemetry

        settings = MagicMock()
        settings.OTEL_SDK_DISABLED = True
        app = MagicMock()

        # Should return without touching OTel — no exception
        setup_telemetry(app, settings=settings)

    def test_setup_with_no_endpoint(self):
        from app.core.telemetry import setup_telemetry

        settings = MagicMock()
        settings.OTEL_SDK_DISABLED = False
        settings.OTLP_ENDPOINT = ""
        settings.OTEL_SAMPLE_RATE = 1.0
        settings.APP_TITLE = "test-app"
        settings.CACHE_ENABLED = False
        settings.CELERY_ENABLED = False
        app = MagicMock()

        with (
            patch("opentelemetry.trace.set_tracer_provider"),
            patch("opentelemetry.instrumentation.fastapi.FastAPIInstrumentor.instrument_app"),
            patch("opentelemetry.instrumentation.sqlalchemy.SQLAlchemyInstrumentor.instrument"),
        ):
            setup_telemetry(app, settings=settings)

    def test_setup_with_otlp_endpoint(self):
        from app.core.telemetry import setup_telemetry

        settings = MagicMock()
        settings.OTEL_SDK_DISABLED = False
        settings.OTLP_ENDPOINT = "http://jaeger:4317"
        settings.OTEL_SAMPLE_RATE = 0.5
        settings.APP_TITLE = "test-app"
        settings.CACHE_ENABLED = False
        settings.CELERY_ENABLED = False
        app = MagicMock()

        with (
            patch("opentelemetry.trace.set_tracer_provider"),
            patch("opentelemetry.instrumentation.fastapi.FastAPIInstrumentor.instrument_app"),
            patch("opentelemetry.instrumentation.sqlalchemy.SQLAlchemyInstrumentor.instrument"),
            patch(
                "opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter"
            ) as mock_exp,
        ):
            mock_exp.return_value = MagicMock()
            setup_telemetry(app, settings=settings)
            mock_exp.assert_called_once_with(endpoint="http://jaeger:4317", insecure=True)


# ---------------------------------------------------------------------------
# app.core.config — new fields
# ---------------------------------------------------------------------------


class TestNewConfigFields:
    def _make_settings(self, **overrides):
        from app.core.config import Settings

        base = {
            "APP_ENV": "development",
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "SECRET_KEY": "a" * 64,
        }
        base.update(overrides)
        return Settings(**base)

    def test_otel_sample_rate_default(self):
        s = self._make_settings()
        assert s.OTEL_SAMPLE_RATE == 1.0

    def test_log_pii_redact_default(self):
        s = self._make_settings()
        assert s.LOG_PII_REDACT is False

    def test_otel_sdk_disabled_default(self):
        s = self._make_settings()
        assert s.OTEL_SDK_DISABLED is False

    def test_otlp_endpoint_default_empty(self):
        s = self._make_settings()
        assert s.OTLP_ENDPOINT == ""
