# Project Tracker — Reference Implementation

A minimal multi-tenant project tracker built on `fastapi-production-starter`.
Demonstrates how to layer real business features on top of the foundation without
modifying the core.

## What it shows

| Pattern | Where |
|---|---|
| Multi-tenant row isolation | `models/project.py` — `tenant_id` FK on every entity |
| RBAC on a custom resource | `routers/projects.py` — `require_role("member")` guard |
| Audit log integration | `services/project_service.py` — `log_event()` calls |
| Outgoing webhook events | `services/project_service.py` — `dispatch_event()` on status change |
| Feature flag gate | `routers/projects.py` — `is_enabled(db, "projects_v2")` check |
| Background job dispatch | `services/notification_service.py` — `get_job_queue().enqueue(...)` |
| OpenTelemetry span | `services/project_service.py` — `tracer.start_as_current_span(...)` |
| GDPR PII tagging | `models/project.py` — `@mark_pii()` on description field |

## Structure

```
examples/project-tracker/
├── README.md
├── models/
│   ├── __init__.py
│   └── project.py          # Project + Task models
├── schemas/
│   ├── __init__.py
│   └── project.py          # Pydantic request/response schemas
├── services/
│   ├── __init__.py
│   ├── project_service.py  # Business logic, audit, webhooks, OTel
│   └── notification_service.py  # Background job dispatch
└── routers/
    ├── __init__.py
    └── projects.py         # FastAPI router, RBAC guards, feature flags
```

## Running

This example is not a standalone app — it shows how you would add the
`projects` router to the main application:

```python
# In app/main.py, inside create_app():
from examples.project_tracker.routers.projects import router as projects_router
app.include_router(projects_router)
```

Then run `make migrate-new msg="add project tracker tables"` and `make migrate`.
