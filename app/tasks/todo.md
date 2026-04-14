# TODO - `app/tasks/`

Background worker tasks (Celery) belong here.

## How to add a task
1. Create task function in a module (e.g. `report_tasks.py`).
2. Decorate with `@celery_app.task(name="tasks.your_task_name")`.
3. Keep task payloads JSON-serializable.
4. Make task safe for retries and duplicate delivery.

## Rule
- Business workflow should call tasks via queue when async/offloaded work is needed.
