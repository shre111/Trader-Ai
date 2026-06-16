"""
InvestIQ — database access layer.

Thin wrapper around a pooled SQLAlchemy engine. All DB access in the module goes
through these helpers (never raw psycopg2), mirroring the reference project's
`database/db.py` pattern. Targets the isolated `investiq` database.
"""

import os

import pandas as pd
from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from config.settings import DB_URL
from utils.logger import get_logger

logger = get_logger("db")

engine = create_engine(DB_URL, pool_size=5, max_overflow=10, pool_pre_ping=True)


def get_engine():
    return engine


def execute_sql(sql: str, params: dict = None):
    """Execute a single write/DDL statement and commit."""
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        conn.commit()
        return result


def read_sql(query: str, params: dict = None) -> pd.DataFrame:
    """Run a SELECT and return a DataFrame."""
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


def write_df(df: pd.DataFrame, table: str, if_exists: str = "append"):
    """Bulk insert a DataFrame (no conflict handling — use upsert_rows for that)."""
    if df is None or df.empty:
        return 0
    df.to_sql(table, engine, if_exists=if_exists, index=False, method="multi")
    return len(df)


def upsert_rows(
    df: pd.DataFrame,
    table: str,
    conflict_cols: list,
    update: bool = False,
    chunk_size: int = 500,
) -> int:
    """
    Insert rows with ON CONFLICT handling, keyed by `conflict_cols`.

    update=False → ON CONFLICT DO NOTHING (idempotent backfills)
    update=True  → ON CONFLICT DO UPDATE all non-key columns (refresh latest values)

    Returns the number of affected rows.
    """
    if df is None or df.empty:
        return 0

    meta = MetaData()
    meta.reflect(bind=engine, only=[table])
    tbl = meta.tables[table]
    rows = df.to_dict(orient="records")
    affected = 0

    with engine.begin() as conn:
        for start in range(0, len(rows), chunk_size):
            chunk = rows[start:start + chunk_size]
            stmt = pg_insert(tbl).values(chunk)
            if update:
                update_cols = {
                    c.name: stmt.excluded[c.name]
                    for c in tbl.columns
                    if c.name not in conflict_cols
                }
                stmt = stmt.on_conflict_do_update(
                    index_elements=conflict_cols, set_=update_cols
                )
            else:
                stmt = stmt.on_conflict_do_nothing(index_elements=conflict_cols)
            affected += conn.execute(stmt).rowcount
    return affected


def init_db():
    """Execute schema.sql to create all tables and hypertables (idempotent)."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        raw = f.read()
    # Strip full-line comments BEFORE splitting so a ';' inside a comment can't
    # break statement boundaries. Each statement runs in autocommit, so a single
    # failure (e.g. on idempotent re-run) doesn't poison the rest.
    sql = "\n".join(ln for ln in raw.splitlines() if not ln.strip().startswith("--"))
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for statement in sql.split(";"):
            stmt = statement.strip()
            if not stmt:
                continue
            try:
                conn.execute(text(stmt))
            except Exception as e:  # noqa: BLE001 - log and continue on idempotent re-runs
                logger.warning(f"Schema statement skipped: {e}")
    logger.info("InvestIQ database schema initialized.")
