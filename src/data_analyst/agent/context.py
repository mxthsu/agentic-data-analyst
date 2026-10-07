from __future__ import annotations

from typing import Any

from .models import DatabaseSchema, QueryEvidence


def schema_payload(schema: DatabaseSchema) -> dict[str, Any]:
    return {
        "tables": {
            name: {
                "columns": [
                    {
                        "name": column.name,
                        "type": column.data_type,
                        "primary_key": column.primary_key,
                    }
                    for column in table.columns
                ],
                "foreign_keys": [
                    {
                        "column": fk.column,
                        "referenced_table": fk.referenced_table,
                        "referenced_column": fk.referenced_column,
                    }
                    for fk in table.foreign_keys
                ],
            }
            for name, table in schema.tables.items()
        },
        "date_coverage": {
            name: coverage.model_dump() for name, coverage in schema.date_coverage.items()
        },
        "categorical_values": {
            name: list(values) for name, values in schema.categorical_values.items()
        },
    }


def evidence_payload(
    evidence: list[QueryEvidence],
    *,
    max_rows_per_query: int = 50,
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for item in evidence:
        rows = item.result.rows[:max_rows_per_query]
        payload.append(
            {
                "purpose": item.purpose,
                "sql": item.sql,
                "columns": item.result.columns,
                "rows": rows,
                "truncated": item.result.truncated
                or len(item.result.rows) > max_rows_per_query,
            }
        )
    return payload
