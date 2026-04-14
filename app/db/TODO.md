# TODO - `app/db/`

Database plumbing and persistence-wide patterns live here.

## Add in this folder when
- You need shared DB behavior (mixins, tenant filters, session strategies).
- You are changing engine/session construction.

## Typical tasks
- Add new reusable mixins in `mixins.py`.
- Add query helpers (e.g. tenant-aware filtering).
- Extend read/write split behavior in `database.py`.

## Guidelines
- Keep DB initialization lazy and environment-safe.
- Do not embed business logic in DB helpers.
- Keep SQLite and non-SQL compatibility in mind.
