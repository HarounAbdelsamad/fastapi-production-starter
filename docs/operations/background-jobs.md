# Background Jobs

Background jobs run tasks outside the HTTP request cycle — sending emails, cleaning up
stale data, generating reports.  This project decouples callers from the queue backend
via a `JobQueue` protocol so you can swap Celery for RQ (or anything else) without
touching business logic.

## The `JobQueue` protocol

```python
from app.core.jobs import get_job_queue

queue = get_job_queue()
job_id = queue.enqueue("tasks.send_email", to="user@example.com", subject="Welcome")
job_id = queue.enqueue_in(300, "tasks.generate_report", report_id="r-42")
```

`get_job_queue()` returns the configured backend.  Raise an error at the call site if no
backend is enabled rather than silently dropping jobs.

## Celery adapter (default)

Enable with `CELERY_ENABLED=true`.  Tasks live in `app/tasks/`.

```bash
# Start worker
celery -A app.worker worker --loglevel=info

# Start beat scheduler (periodic tasks)
celery -A app.worker beat --loglevel=info
```

Existing tasks:

| Task name | Module | Schedule |
|---|---|---|
| `tasks.send_email` | `app/tasks/email_tasks.py` | on-demand |
| `tasks.cleanup_revoked_tokens` | `app/tasks/cleanup_tasks.py` | daily |

### Adding a new task

```python
# app/tasks/my_tasks.py
from app.worker import celery_app

@celery_app.task(name="tasks.my_new_task")
def my_new_task(user_id: str) -> None:
    ...
```

Enqueue from a service:

```python
from app.core.jobs import get_job_queue

queue = get_job_queue()
queue.enqueue("tasks.my_new_task", user_id="u-123")
```

## RQ adapter (sketch)

RQ is simpler than Celery but requires Redis and Python callables (not name strings).
`app/core/jobs.py` contains `RQJobQueue` as a ready-to-fill template:

1. `uv add rq`
2. Implement `enqueue` / `enqueue_in` in `RQJobQueue`
3. Set `JOB_QUEUE_BACKEND=rq`

See the inline comments in [app/core/jobs.py](../../app/core/jobs.py) for the exact
calls to make.

## Choosing between Celery and RQ

| Concern | Celery | RQ |
|---|---|---|
| Broker options | Redis, RabbitMQ, SQS, … | Redis only |
| Scheduled / periodic tasks | Built-in (Beat) | `rq-scheduler` |
| Task routing / priorities | Rich | Simple queues |
| Monitoring UI | Flower | RQ Dashboard |
| Learning curve | Higher | Lower |

Default to Celery if you need multi-broker support, complex routing, or rate limiting per
task.  RQ is a good fit for simple Redis-only deployments.

## Graceful worker shutdown

Send `SIGTERM` to the Celery worker process.  The worker finishes its current task, then
exits cleanly:

```bash
celery -A app.worker control shutdown
# or
kill -TERM <worker-pid>
```

Set `--max-tasks-per-child` to avoid memory leaks in long-running workers.
