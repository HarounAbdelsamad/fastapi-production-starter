"""
Zero-downtime migration helper utilities.

See docs/migrations/zero-downtime.md for the full playbook.

These helpers implement the patterns that are tedious to write correctly from
scratch: batched backfills with progress tracking, safe column renames, and
idempotent data migrations.

Usage
-----
Run a backfill directly from an Alembic migration script or from the CLI:

    from app.db.migration_helpers import backfill_in_batches

    async def run_backfill(bind) -> None:
        async for batch_num, count in backfill_in_batches(
            bind,
            table="users",
            pk_column="user_id",
            update_sql="UPDATE users SET new_col = 'default' WHERE new_col IS NULL",
            batch_size=500,
        ):
            print(f"Batch {batch_num}: updated {count} rows")
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)


async def backfill_in_batches(
    conn: AsyncConnection,
    *,
    table: str,
    pk_column: str,
    update_sql: str,
    batch_size: int = 500,
    where_clause: str = "",
    progress_log: bool = True,
) -> AsyncGenerator[tuple[int, int]]:
    """Backfill rows in *table* in batches to avoid long-running transactions.

    This is the safe way to add a new column with a non-null default to an
    existing table without locking it for the duration of the backfill.

    Args:
        conn:           An active async SQLAlchemy connection (``AsyncConnection``).
        table:          Table name to update.
        pk_column:      Name of the primary key column (used for cursor-based pagination).
        update_sql:     The UPDATE statement to run per batch.
                        Must include a ``WHERE {pk_column} > :cursor_start
                        AND {pk_column} <= :cursor_end`` clause — OR pass
                        ``where_clause`` to let this helper build the cursor
                        conditions automatically.

                        Simpler: pass ``update_sql`` as the SET portion only
                        (e.g. ``"new_col = 'default'"``), and this helper
                        wraps it with cursor conditions.
        batch_size:     Number of rows per batch.  Default: 500.
        where_clause:   Additional WHERE condition to filter rows
                        (e.g. ``"status = 'active'"``)..
        progress_log:   If True, emit an INFO log per batch.

    Yields:
        ``(batch_number, rows_updated)`` tuples.

    Example — add a NOT NULL column with a default::

        async for batch, count in backfill_in_batches(
            conn,
            table="users",
            pk_column="user_id",
            update_sql="tier = 'free'",
            where_clause="tier IS NULL",
        ):
            pass  # optional: track progress

    The caller is responsible for the surrounding Alembic op context.
    """
    extra_filter = f" AND ({where_clause})" if where_clause else ""

    # Determine the min/max PK range to iterate over.
    bounds = await conn.execute(
        text(f"SELECT MIN({pk_column}), MAX({pk_column}) FROM {table}")  # noqa: S608
    )
    row = bounds.fetchone()
    if row is None or row[0] is None:
        if progress_log:
            logger.info("backfill %s: table is empty, nothing to do", table)
        return

    min_pk, max_pk = row[0], row[1]

    # Cursor-based batching: fetch PKs in pages, run UPDATE per page.
    batch_num = 0
    cursor = min_pk

    # Fetch primary keys in pages to avoid a full-table scan per batch.
    while True:
        pk_rows = await conn.execute(
            text(
                f"SELECT {pk_column} FROM {table} "  # noqa: S608
                f"WHERE {pk_column} >= :cursor{extra_filter} "
                f"ORDER BY {pk_column} ASC LIMIT :batch_size"
            ),
            {"cursor": cursor, "batch_size": batch_size},
        )
        pks = [r[0] for r in pk_rows.fetchall()]
        if not pks:
            break

        pk_list = ", ".join(f"'{pk}'" if isinstance(pk, str) else str(pk) for pk in pks)

        result = await conn.execute(
            text(
                f"UPDATE {table} SET {update_sql} "  # noqa: S608
                f"WHERE {pk_column} IN ({pk_list})"
            )
        )
        rows_updated = result.rowcount
        batch_num += 1

        if progress_log:
            logger.info(
                "backfill %s: batch %d — updated %d rows (cursor=%s)",
                table,
                batch_num,
                rows_updated,
                pks[-1],
            )

        yield batch_num, rows_updated

        if pks[-1] >= max_pk:
            break
        cursor = pks[-1]

    if progress_log:
        logger.info("backfill %s: complete after %d batches", table, batch_num)


async def column_exists(conn: AsyncConnection, table: str, column: str) -> bool:
    """Return True if *column* exists in *table* (cross-DB compatible).

    Useful for writing idempotent migrations::

        if not await column_exists(conn, "users", "new_col"):
            await conn.execute(text("ALTER TABLE users ADD COLUMN new_col TEXT"))
    """
    result = await conn.execute(
        text("SELECT * FROM information_schema.columns WHERE table_name = :table AND column_name = :col"),  # noqa: E501
        {"table": table, "col": column},
    )
    return result.fetchone() is not None


async def table_row_count(conn: AsyncConnection, table: str, where: str = "") -> int:
    """Return approximate row count for *table* (useful for progress estimates)."""
    filter_clause = f" WHERE {where}" if where else ""
    result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}{filter_clause}"))  # noqa: S608
    row = result.fetchone()
    return int(row[0]) if row else 0


async def run_idempotent_migration(
    conn: AsyncConnection,
    migration_id: str,
    sql: str,
    tracking_table: str = "_migration_log",
) -> bool:
    """Run a data migration exactly once, tracking completion in a log table.

    Creates *tracking_table* on first call. Returns True if the migration ran,
    False if it was already recorded as complete.

    This is useful for data-only migrations (backfills, enum conversions) that
    should survive repeated Alembic runs::

        async with engine.begin() as conn:
            ran = await run_idempotent_migration(
                conn,
                migration_id="backfill_users_tier_2024_01",
                sql="UPDATE users SET tier = 'free' WHERE tier IS NULL",
            )
    """
    # Ensure tracking table exists
    await conn.execute(
        text(
            f"CREATE TABLE IF NOT EXISTS {tracking_table} "  # noqa: S608
            f"(migration_id VARCHAR(255) PRIMARY KEY, ran_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
    )

    # Check if already run
    existing = await conn.execute(
        text(f"SELECT migration_id FROM {tracking_table} WHERE migration_id = :id"),  # noqa: S608
        {"id": migration_id},
    )
    if existing.fetchone() is not None:
        logger.info("idempotent migration '%s': already recorded, skipping", migration_id)
        return False

    # Run the migration
    await conn.execute(text(sql))

    # Record completion
    await conn.execute(
        text(
            f"INSERT INTO {tracking_table} (migration_id) VALUES (:id)"  # noqa: S608
        ),
        {"id": migration_id},
    )
    logger.info("idempotent migration '%s': complete", migration_id)
    return True


class BackfillProgress:
    """Tracks and reports backfill progress for long-running migrations."""

    def __init__(self, table: str, total_rows: int) -> None:
        self.table = table
        self.total_rows = total_rows
        self.processed = 0
        self.batches = 0
        self._start = __import__("time").monotonic()

    def update(self, rows_in_batch: int) -> None:
        self.processed += rows_in_batch
        self.batches += 1

    @property
    def pct(self) -> float:
        if self.total_rows == 0:
            return 100.0
        return round(self.processed / self.total_rows * 100, 1)

    @property
    def elapsed_s(self) -> float:
        return round(__import__("time").monotonic() - self._start, 1)

    def log(self) -> None:
        logger.info(
            "backfill %s: %d/%d rows (%.1f%%) in %d batches — %.1fs elapsed",
            self.table,
            self.processed,
            self.total_rows,
            self.pct,
            self.batches,
            self.elapsed_s,
        )


async def safe_backfill(
    conn: AsyncConnection,
    *,
    table: str,
    pk_column: str,
    update_sql: str,
    where_clause: str = "",
    batch_size: int = 500,
) -> BackfillProgress:
    """Run a full backfill with progress tracking.  Returns a BackfillProgress summary.

    Example::

        async with engine.begin() as conn:
            progress = await safe_backfill(
                conn,
                table="users",
                pk_column="user_id",
                update_sql="tier = 'free'",
                where_clause="tier IS NULL",
            )
        print(f"Backfilled {progress.processed} rows in {progress.elapsed_s}s")
    """
    total = await table_row_count(conn, table, where=where_clause)
    progress = BackfillProgress(table=table, total_rows=total)

    async for _batch_num, rows_updated in backfill_in_batches(
        conn,
        table=table,
        pk_column=pk_column,
        update_sql=update_sql,
        where_clause=where_clause,
        batch_size=batch_size,
        progress_log=False,
    ):
        progress.update(rows_updated)
        progress.log()

    return progress


def expand_contract_checklist(old_column: str, new_column: str, table: str) -> list[dict[str, Any]]:
    """Return a step-by-step checklist for a zero-downtime column rename.

    Each step is a dict with ``phase``, ``description``, and ``sql`` (or None).
    Print or log this for operator review before executing.

    See docs/migrations/zero-downtime.md for the full explanation.
    """
    return [
        {
            "phase": "expand",
            "step": 1,
            "description": f"Add {new_column} as nullable column",
            "sql": f"ALTER TABLE {table} ADD COLUMN {new_column} VARCHAR(255)",
            "deploy": False,
        },
        {
            "phase": "expand",
            "step": 2,
            "description": f"Backfill {new_column} from {old_column}",
            "sql": f"UPDATE {table} SET {new_column} = {old_column} WHERE {new_column} IS NULL",
            "deploy": False,
        },
        {
            "phase": "expand",
            "step": 3,
            "description": (
                f"Deploy code that writes to BOTH {old_column} and {new_column}, "
                f"reads from {old_column}"
            ),
            "sql": None,
            "deploy": True,
        },
        {
            "phase": "contract",
            "step": 4,
            "description": f"Deploy code that writes to BOTH, reads from {new_column}",
            "sql": None,
            "deploy": True,
        },
        {
            "phase": "contract",
            "step": 5,
            "description": f"Deploy code that writes only to {new_column}, reads from {new_column}",
            "sql": None,
            "deploy": True,
        },
        {
            "phase": "contract",
            "step": 6,
            "description": f"Drop {old_column}",
            "sql": f"ALTER TABLE {table} DROP COLUMN {old_column}",
            "deploy": False,
        },
    ]
