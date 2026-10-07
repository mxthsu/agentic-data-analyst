from __future__ import annotations

import sqlite3
import time
from collections.abc import Mapping
from pathlib import Path

from data_analyst.agent.models import QueryResult
from data_analyst.safety.sql_guard import SQLGuard, SQLPolicyError

type Scalar = str | int | float | bool | None


class QueryExecutionError(RuntimeError):
    pass


def _connect_read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def execute_query(
    path: Path,
    sql: str,
    *,
    params: Mapping[str, Scalar] | None = None,
    row_limit: int = 500,
    timeout_seconds: float = 5.0,
    guard: SQLGuard | None = None,
) -> QueryResult:
    if row_limit < 1 or timeout_seconds <= 0:
        raise ValueError("Limites de consulta inválidos.")

    active_guard = guard or SQLGuard()
    try:
        active_guard.ensure_safe(sql)
    except SQLPolicyError as exc:
        raise QueryExecutionError(str(exc)) from exc

    started = time.monotonic()
    try:
        db = _connect_read_only(path)
    except sqlite3.Error as exc:
        raise QueryExecutionError("Não foi possível abrir o banco.") from exc

    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
    if hasattr(sqlite3, "SQLITE_RECURSIVE"):
        allowed.add(sqlite3.SQLITE_RECURSIVE)

    try:
        db.execute("PRAGMA query_only=ON")
        db.set_authorizer(
            lambda action, *_: sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY
        )
        db.set_progress_handler(
            lambda: int(time.monotonic() - started >= timeout_seconds),
            100,
        )
        cursor = db.execute(sql, dict(params or {}))
        columns = tuple(item[0] for item in cursor.description or ())
        rows = cursor.fetchmany(row_limit + 1)
        duration_ms = (time.monotonic() - started) * 1000
        return QueryResult(
            columns=columns,
            rows=tuple(tuple(row) for row in rows[:row_limit]),
            truncated=len(rows) > row_limit,
            duration_ms=duration_ms,
        )
    except sqlite3.Error as exc:
        if "interrupted" in str(exc).lower():
            raise QueryExecutionError("Consulta excedeu o limite de tempo.") from exc
        raise QueryExecutionError(f"Falha ao executar SQL: {exc}") from exc
    finally:
        db.close()
