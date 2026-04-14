# MongoDB Migration Template Guide

Alembic does not manage MongoDB migrations because Alembic is SQLAlchemy-specific.

Use one of these approaches:

1. **Beanie migrations** for document schema changes.
2. **Custom migration scripts** using `motor` with an explicit migration registry.
3. **One-off data migration jobs** via Celery tasks for large collections.

Recommended structure:

```
mongodb_migrations/
  0001_add_field_x.py
  0002_backfill_field_x.py
  0003_drop_legacy_field.py
```

Each script should:

- define a unique migration id
- include `upgrade()` and optional `downgrade()` functions
- record applied migration IDs in a dedicated `schema_migrations` collection
