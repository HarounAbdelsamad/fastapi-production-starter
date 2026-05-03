# ADR-009: Background Jobs as a Protocol, Not a Baked-In Choice

## Status
Accepted

## Context

Background job processing is a standard enterprise requirement: sending emails, processing uploaded files, running scheduled reports, performing bulk data operations, handling webhooks. The question is not whether to include background jobs, but how.

The main options are:

1. **Pick a specific library and bake it in**: Celery, Dramatiq, Arq, RQ
2. **Define a protocol and provide adapters**: Let teams bring their own queue backend

The Python background job ecosystem has fragmented significantly:

| Library | Backend | Async | Notes |
|---|---|---|---|
| Celery | Redis, RabbitMQ, SQS | No (uses threads/processes) | Most widely deployed; complex config |
| Dramatiq | Redis, RabbitMQ | No | Cleaner API than Celery |
| Arq | Redis | Yes (asyncio-native) | Modern, simple, asyncio-first |
| RQ (Redis Queue) | Redis only | No | Simple, good for small workloads |
| Taskiq | Multiple | Yes | Async-first, protocol-based |
| Cloud queues | SQS, GCP Tasks, Azure SB | Depends | Enterprise teams often prefer managed |

Enterprise teams have strong opinions about their job queue. A template that forces Celery will be abandoned by teams that standardized on Dramatiq or cloud-native queues.

## Decision

**Define a `JobQueue` protocol. Implement a Celery adapter as the default. Provide an RQ adapter as a reference implementation. Document the protocol contract for teams to implement their own adapter in ~100 lines.**

## Protocol Design

```python
from typing import Protocol, Any, Callable

class JobQueue(Protocol):
    def enqueue(
        self,
        func: Callable,
        *args: Any,
        queue: str = "default",
        countdown: int = 0,
        retry: int = 3,
        **kwargs: Any,
    ) -> str:
        """Enqueue a job. Returns a job ID."""
        ...

    def enqueue_at(
        self,
        func: Callable,
        eta: datetime,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """Enqueue a job at a specific time."""
        ...

    def revoke(self, job_id: str) -> None:
        """Cancel a pending job."""
        ...
```

The protocol is intentionally minimal. It covers the 90% case: fire-and-forget with optional delay and retry. Complex Celery-specific features (chords, chains, canvases) are not in the protocol — teams that need them should use Celery directly.

## Celery Adapter (Default)

The default implementation wraps Celery's `apply_async`:

```python
class CeleryJobQueue:
    def __init__(self, app: Celery) -> None:
        self.app = app

    def enqueue(self, func: Callable, *args, queue="default", countdown=0, retry=3, **kwargs) -> str:
        result = self.app.send_task(
            func.__name__,
            args=args,
            kwargs=kwargs,
            queue=queue,
            countdown=countdown,
            max_retries=retry,
        )
        return result.id
```

Celery is the default because:
- **Widest deployment**: Most senior Python engineers have used Celery. The learning curve is known.
- **Feature completeness**: Periodic tasks (celery-beat), priority queues, rate limiting, result backends — all supported.
- **Multiple brokers**: Redis and RabbitMQ are both first-class. SQS is supported. Teams can switch brokers without changing application code.
- **Monitoring**: Flower provides a web UI. Enterprise APM tools (Datadog, New Relic, Sentry) all have Celery integrations.

Celery is disabled by default (`CELERY_ENABLED=false`). No Celery workers start unless enabled.

## RQ Adapter (Reference Implementation)

RQ (Redis Queue) is simpler than Celery and Redis-only. The RQ adapter demonstrates that the protocol is implementable with a different library:

```python
class RQJobQueue:
    def __init__(self, redis_conn: Redis) -> None:
        self.queues: dict[str, Queue] = {}
        self.redis = redis_conn

    def enqueue(self, func: Callable, *args, queue="default", countdown=0, retry=3, **kwargs) -> str:
        q = self._get_queue(queue)
        job = q.enqueue_in(timedelta(seconds=countdown), func, *args, **kwargs)
        return job.id
```

The RQ adapter is ~80 lines. This is the "adapter is easy to write" proof.

## Injecting the Queue

The queue implementation is injected via FastAPI's dependency injection:

```python
def get_job_queue() -> JobQueue:
    if settings.CELERY_ENABLED:
        return CeleryJobQueue(celery_app)
    return NoOpJobQueue()  # for testing / disabled state

@router.post("/users/import")
async def import_users(
    file: UploadFile,
    queue: JobQueue = Depends(get_job_queue),
):
    job_id = queue.enqueue(process_user_import, file.filename)
    return {"job_id": job_id}
```

`NoOpJobQueue` runs the function synchronously (for testing) or drops it (for disabled state). Configurable.

## Scheduling

Periodic tasks (cron-style) are outside the `JobQueue` protocol scope. Each library handles scheduling differently:

- Celery: celery-beat scheduler
- RQ: rq-scheduler
- Arq: built-in cron support

The template documents the Celery-beat setup. Other schedulers are left to the team's adapter implementation.

## Consequences

**Positive:**
- Teams can swap to Dramatiq, Arq, or a cloud queue without changing any application code that uses `JobQueue`.
- `NoOpJobQueue` makes unit testing trivial — no broker required.
- Celery adapter covers all standard use cases out of the box.
- The RQ adapter proves the protocol is minimal enough to implement quickly.

**Negative:**
- Celery-specific features (canvas, chords) are not exposed via the protocol. Teams that need them must use `celery_app` directly. Acceptable trade-off.
- The protocol abstraction adds one layer between application code and Celery. Stack traces are slightly deeper.
- Periodic tasks are not in the protocol. Teams using non-Celery backends need to set up their own scheduler. Documented.

## References

- [Celery documentation](https://docs.celeryq.dev/en/stable/)
- [RQ documentation](https://python-rq.org/)
- [Arq documentation](https://arq-docs.helpmanual.io/)
- [PEP 544 — Protocols](https://peps.python.org/pep-0544/)
