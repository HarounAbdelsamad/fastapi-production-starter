# TODO - `app/models/`

SQLAlchemy ORM entities belong here.

## How to add a new model
1. Create a new file (e.g. `order.py`).
2. Define model class inheriting from `Base` (+ mixins as needed).
3. Add model export in `app/models/__init__.py`.
4. Ensure model import is included in `init_db()` registration.
5. Create Alembic migration for schema changes.

## Rules
- Keep models focused on data shape and light behavior only.
- Put heavy business rules in services.
