# TODO - `alembic/versions/`

Each file here is a migration revision.

## How to work here
- Add only one coherent schema change per revision when possible.
- Include safe downgrade steps whenever practical.
- Keep migration IDs and dependencies correct (`revision`, `down_revision`).

## Rule
- Never edit applied migrations in shared environments; add a new migration instead.
