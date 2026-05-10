"""Tests for the JobQueue protocol and adapters."""

import pytest


class TestJobQueueProtocol:
    def test_celery_job_queue_satisfies_protocol(self):
        from app.core.jobs import CeleryJobQueue, JobQueue

        assert isinstance(CeleryJobQueue(), JobQueue)

    def test_get_job_queue_raises_when_no_backend(self):
        from unittest.mock import patch

        from app.core.jobs import get_job_queue

        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.CELERY_ENABLED = False
            with pytest.raises(RuntimeError, match="No job queue backend"):
                get_job_queue()

    def test_get_job_queue_returns_celery_when_enabled(self):
        from unittest.mock import patch

        from app.core.jobs import CeleryJobQueue, get_job_queue

        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.CELERY_ENABLED = True
            queue = get_job_queue()
            assert isinstance(queue, CeleryJobQueue)

    def test_rq_job_queue_raises_without_rq_installed(self):
        from unittest.mock import patch

        from app.core.jobs import RQJobQueue

        with patch.dict("sys.modules", {"rq": None, "redis": None}):
            with pytest.raises((RuntimeError, ImportError)):
                RQJobQueue()

    def test_rq_enqueue_raises_not_implemented(self):
        from unittest.mock import MagicMock, patch

        from app.core.jobs import RQJobQueue

        mock_redis = MagicMock()
        mock_rq = MagicMock()
        mock_rq.Queue.return_value = MagicMock()

        with patch.dict("sys.modules", {"rq": mock_rq, "redis": mock_redis}):
            with patch("app.core.config.get_settings") as mock_settings:
                mock_settings.return_value.REDIS_URL = "redis://localhost:6379"
                queue = RQJobQueue()
                with pytest.raises(NotImplementedError):
                    queue.enqueue("some.task", "arg1")
                with pytest.raises(NotImplementedError):
                    queue.enqueue_in(60, "some.task", "arg1")
