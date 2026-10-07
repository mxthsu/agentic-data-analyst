from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path

from data_analyst.agent.models import (
    ColumnInfo,
    DatabaseSchema,
    DateCoverage,
    ForeignKeyInfo,
    TableSchema,
)

MAX_CATEGORICAL_VALUES = 20
_SENSITIVE_COLUMN_MARKERS = {
    "nome",
    "email",
    "e_mail",
    "telefone",
    "celular",
    "cpf",
    "cnpj",
    "rg",
    "endereco",
    "endereço",
    "cep",
}


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _connect_read_only(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _is_date_candidate(column: str) -> bool:
    name = column.lower()
    return "data" in name or "date" in name


def _is_sensitive_column(column: str) -> bool:
    normalized = column.lower().replace("-", "_").replace(" ", "_")
    return any(marker in normalized for marker in _SENSITIVE_COLUMN_MARKERS)


def _is_categorical_candidate(column: ColumnInfo) -> bool:
    if column.primary_key or _is_date_candidate(column.name) or _is_sensitive_column(column.name):
        return False

    data_type = column.data_type.upper()
    return any(marker in data_type for marker in ("TEXT", "CHAR", "CLOB", "INT", "BOOL"))


def _date_coverage(db: sqlite3.Connection, table: str, column: str) -> DateCoverage:
    table_q, column_q = _quote(table), _quote(column)
    rows = db.execute(
        f"SELECT date({column_q}), strftime('%Y', {column_q}), "
        f"strftime('%m', {column_q}) FROM {table_q} "
        f"WHERE date({column_q}) IS NOT NULL"
    )
    dates: list[str] = []
    years_by_month: defaultdict[int, set[int]] = defaultdict(set)
    for date_value, year, month in rows:
        dates.append(date_value)
        years_by_month[int(month)].add(int(year))
    return DateCoverage(
        min_date=min(dates) if dates else None,
        max_date=max(dates) if dates else None,
        years_by_month={
            month: tuple(sorted(years)) for month, years in years_by_month.items()
        },
    )


def _categorical_values(
    db: sqlite3.Connection,
    table: str,
    column: ColumnInfo,
) -> tuple[str | int, ...]:
    if not _is_categorical_candidate(column):
        return ()

    table_q, column_q = _quote(table), _quote(column.name)
    rows = db.execute(
        f"SELECT DISTINCT {column_q} FROM {table_q} "
        f"WHERE {column_q} IS NOT NULL "
        f"ORDER BY {column_q} LIMIT {MAX_CATEGORICAL_VALUES + 1}"
    ).fetchall()

    if len(rows) > MAX_CATEGORICAL_VALUES:
        return ()

    values: list[str | int] = []
    for (value,) in rows:
        if isinstance(value, bool):
            values.append(int(value))
        elif isinstance(value, (str, int)):
            values.append(value)
        else:
            return ()

    return tuple(values)


def inspect_database(path: Path) -> DatabaseSchema:
    tables: dict[str, TableSchema] = {}
    coverage: dict[str, DateCoverage] = {}
    categorical_values: dict[str, tuple[str | int, ...]] = {}

    with _connect_read_only(path) as db:
        names = [
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for table in names:
            table_q = _quote(table)
            columns = tuple(
                ColumnInfo(
                    name=row[1],
                    data_type=row[2],
                    not_null=bool(row[3]),
                    primary_key=bool(row[5]),
                )
                for row in db.execute(f"PRAGMA table_info({table_q})")
            )
            foreign_keys = tuple(
                ForeignKeyInfo(
                    column=row[3],
                    referenced_table=row[2],
                    referenced_column=row[4],
                )
                for row in db.execute(f"PRAGMA foreign_key_list({table_q})")
            )
            tables[table] = TableSchema(
                name=table,
                columns=columns,
                foreign_keys=foreign_keys,
            )

            foreign_key_columns = {fk.column for fk in foreign_keys}
            for column in columns:
                key = f"{table}.{column.name}"
                if _is_date_candidate(column.name):
                    coverage[key] = _date_coverage(db, table, column.name)

                if column.name in foreign_key_columns:
                    continue

                values = _categorical_values(db, table, column)
                if values:
                    categorical_values[key] = values

    return DatabaseSchema(
        tables=tables,
        date_coverage=coverage,
        categorical_values=categorical_values,
    )
