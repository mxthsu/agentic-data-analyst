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


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _connect_read_only(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _is_date_candidate(column: str) -> bool:
    name = column.lower()
    return "data" in name or "date" in name


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


def inspect_database(path: Path) -> DatabaseSchema:
    tables: dict[str, TableSchema] = {}
    coverage: dict[str, DateCoverage] = {}

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
            for column in columns:
                if _is_date_candidate(column.name):
                    coverage[f"{table}.{column.name}"] = _date_coverage(
                        db, table, column.name
                    )

    return DatabaseSchema(tables=tables, date_coverage=coverage)
