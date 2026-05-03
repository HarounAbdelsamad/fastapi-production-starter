# Zero-Downtime Migrations

Enterprise services cannot take downtime for database schema changes. This playbook documents the patterns for making schema changes without dropping availability.

The helper utilities referenced here are in [`app/db/migration_helpers.py`](../../app/db/migration_helpers.py).

---

## The Core Rule

**Never make a schema change that breaks the currently-running code.**

At deployment time, there are two versions of your code running simultaneously: the old version (serving traffic) and the new version (starting up). The database change must be compatible with both.

The **expand-contract** pattern solves this by splitting every breaking change into two phases:

- **Expand**: Add new structure; keep old structure. Both old and new code work.
- **Contract**: Remove old structure once old code is fully retired.

---

## Pattern 1: Adding a NOT NULL Column with a Default

**Scenario**: You need to add a `tier` column to the `users` table. `tier` is NOT NULL with a default of `'free'`.

**The wrong way** (takes a table lock, may time out, breaks old code):
```sql
ALTER TABLE users ADD COLUMN tier VARCHAR(50) NOT NULL DEFAULT 'free';
```

On Postgres, `NOT NULL DEFAULT` with a volatile default locks the table for the backfill. On large tables, this can take minutes.

### Step 1: Expand — add nullable column (zero downtime)

```python
# alembic/versions/0005_add_user_tier.py

def upgrade() -> None:
    op.add_column("users", sa.Column("tier", sa.String(50), nullable=True))
```

This migration completes instantly — Postgres adds a nullable column with no lock.

Deploy this migration. Both old code (ignores `tier`) and new code (reads `tier`) work.

### Step 2: Backfill existing rows (zero downtime)

Run the backfill as a standalone script, **not inside Alembic**. This keeps the migration history clean and avoids long-running migration transactions:

```python
# scripts/backfill_user_tier.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.migration_helpers import safe_backfill

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        progress = await safe_backfill(
            conn,
            table="users",
            pk_column="user_id",
            update_sql="tier = 'free'",
            where_clause="tier IS NULL",
            batch_size=500,
        )
    print(f"Backfilled {progress.processed} rows in {progress.elapsed_s}s")
    await engine.dispose()

asyncio.run(main())
```

### Step 3: Contract — add NOT NULL constraint

Once all rows are populated and the new code is live:

```python
# alembic/versions/0006_user_tier_not_null.py

def upgrade() -> None:
    # Postgres 11+ can validate the constraint without a full table lock:
    op.execute("ALTER TABLE users ALTER COLUMN tier SET NOT NULL")
    # For MySQL:
    # op.alter_column("users", "tier", nullable=False)
    # For SQLite (requires batch mode):
    # with op.batch_alter_table("users") as batch_op:
    #     batch_op.alter_column("tier", nullable=False)
```

**Postgres optimisation**: Use `ADD CONSTRAINT ... NOT VALID` + `VALIDATE CONSTRAINT` for tables > 1M rows. This splits the constraint addition from validation, avoiding a long lock:

```python
def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT users_tier_not_null CHECK (tier IS NOT NULL) NOT VALID"
    )
    # Commit, then in a subsequent migration or manually:
    op.execute("ALTER TABLE users VALIDATE CONSTRAINT users_tier_not_null")
```

---

## Pattern 2: Renaming a Column

**Scenario**: You need to rename `users.phone_number` to `users.phone`.

Direct rename (`ALTER TABLE users RENAME COLUMN phone_number TO phone`) breaks old code that still references `phone_number`. Use expand-contract.

Use the checklist helper to generate the step-by-step plan:

```python
from app.db.migration_helpers import expand_contract_checklist

steps = expand_contract_checklist(
    old_column="phone_number",
    new_column="phone",
    table="users",
)
for step in steps:
    print(f"[{step['phase'].upper()} {step['step']}] {step['description']}")
    if step['sql']:
        print(f"  SQL: {step['sql']}")
    if step['deploy']:
        print("  → Deploy new code version")
```

### The 6 Steps

**Phase: Expand** (one migration, no code change):

1. Add `phone` as a nullable column:
   ```sql
   ALTER TABLE users ADD COLUMN phone VARCHAR(50);
   ```

2. Backfill `phone` from `phone_number`:
   ```sql
   UPDATE users SET phone = phone_number WHERE phone IS NULL;
   ```
   (Run as a batched backfill for large tables — see Pattern 1.)

3. **Deploy v2**: code writes to **both** `phone_number` and `phone`; reads from `phone_number`.

**Phase: Contract** (code-only changes, then schema cleanup):

4. **Deploy v3**: code writes to both, reads from `phone`.

5. **Deploy v4**: code writes only to `phone`, reads from `phone`. Old `phone_number` column is ignored.

6. Drop `phone_number`:
   ```sql
   ALTER TABLE users DROP COLUMN phone_number;
   ```

Between steps 3–5, both columns carry the same data. The deployment window is the time it takes for all instances to roll over from v2 → v3 → v4.

---

## Pattern 3: Changing a Column Type

**Scenario**: Change `users.user_id` from `VARCHAR(36)` to `VARCHAR(64)`.

For column widening (VARCHAR(36) → VARCHAR(64)), most databases can do this without a table rewrite:

```python
# Postgres: instant
def upgrade() -> None:
    op.alter_column("users", "user_id", type_=sa.String(64))
```

For column narrowing, or changing the underlying type (e.g., `VARCHAR` → `INTEGER`), use expand-contract:
1. Add a new column with the target type
2. Backfill the converted values
3. Swap reads/writes to the new column
4. Drop the old column

---

## Pattern 4: Adding an Index

Adding an index locks the table on most databases. On Postgres, use `CONCURRENTLY`:

```python
def upgrade() -> None:
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_users_email ON users (email)"
    )

def downgrade() -> None:
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_users_email")
```

`CONCURRENTLY` means:
- The index builds in the background
- Reads and writes continue normally
- The migration takes longer but doesn't block

**Note**: `CONCURRENTLY` cannot run inside a transaction. Alembic wraps migrations in transactions by default. Disable this for the migration:

```python
# At the top of the migration file:
def upgrade() -> None:
    ...

# Tell Alembic not to wrap this migration in a transaction:
migration_module = sys.modules[__name__]
if hasattr(migration_module, "connection"):
    migration_module.connection.execute(text("COMMIT"))  # noqa: S608

# Or use op.get_context() to check:
def upgrade() -> None:
    # op.execute with a raw connection outside the transaction
    with op.get_bind().connect() as conn:
        conn.execute(text("COMMIT"))
        conn.execute(text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_users_email ON users (email)"
        ))
```

Practical approach: run `CREATE INDEX CONCURRENTLY` directly from psql before or after the Alembic migration, and update the migration to be a no-op (just records the migration in the alembic_version table).

MySQL uses `ALGORITHM=INPLACE` for online DDL:
```sql
CREATE INDEX ix_users_email ON users (email) ALGORITHM=INPLACE LOCK=NONE;
```

---

## Helper Reference

### `backfill_in_batches(conn, *, table, pk_column, update_sql, ...)`

Async generator. Yields `(batch_number, rows_updated)` per batch. Use in migration scripts or standalone backfill scripts.

### `safe_backfill(conn, *, table, pk_column, update_sql, ...)`

Runs the full backfill and returns a `BackfillProgress` summary with row counts and elapsed time.

### `expand_contract_checklist(old_column, new_column, table)`

Returns a list of dicts describing each step of a column rename. Use as an operator checklist.

### `run_idempotent_migration(conn, migration_id, sql)`

Runs a SQL statement exactly once, tracking completion in a `_migration_log` table. Safe to run multiple times — subsequent runs are no-ops.

### `column_exists(conn, table, column)`

Returns `True` if the column already exists. Useful for idempotent ALTER TABLE scripts.

---

## Alembic Best Practices for Zero-Downtime

1. **Never combine schema change + data migration in one Alembic migration**. Schema changes should be schema-only. Data migrations (backfills) should be scripts.

2. **Test downgrade**. Every `upgrade()` must have a matching `downgrade()`. If downgrade is not safe (e.g., data loss), document it explicitly.

3. **Run `alembic history`** after writing a migration to verify the chain is intact.

4. **Do not edit committed migrations**. Create a new migration to fix errors. Editing a committed migration breaks teams that have already run it.

5. **Use `op.execute()` sparingly**. Raw SQL in migrations is harder to test and less portable. Prefer `op.add_column`, `op.create_index`, etc.
