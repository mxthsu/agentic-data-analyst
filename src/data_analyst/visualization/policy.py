from __future__ import annotations

import unicodedata
from numbers import Number

from data_analyst.agent.models import QueryEvidence, VisualizationSpec

_TEMPORAL_HINTS = ("data", "date", "mes", "mês", "ano", "year", "month")


def _is_numeric_column(evidence: QueryEvidence, index: int) -> bool:
    values = [row[index] for row in evidence.result.rows if row[index] is not None]
    return bool(values) and all(isinstance(value, Number) for value in values)


def _temporal_column(columns: tuple[str, ...]) -> str | None:
    for column in columns:
        normalized = column.lower()
        if any(hint in normalized for hint in _TEMPORAL_HINTS):
            return column
    return None


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _requested_visualization(question: str) -> str | None:
    normalized = _normalize(question)

    if "tabela" in normalized:
        return "table"

    if any(
        term in normalized
        for term in ("grafico de barras", "grafico de barra", "bar chart", "em barras")
    ):
        return "bar"

    if any(
        term in normalized
        for term in ("grafico de linha", "line chart")
    ):
        return "line"

    return None


def _series_column(
    columns: tuple[str, ...],
    *,
    x: str,
    y: str,
) -> str | None:
    return next(
        (column for column in columns if column not in (x, y)),
        None,
    )


def choose_visualization(
    question: str,
    evidence: list[QueryEvidence],
) -> VisualizationSpec:
    if not evidence:
        return VisualizationSpec(kind="table")

    latest = evidence[-1]
    columns = latest.result.columns
    rows = latest.result.rows
    question_lower = question.lower()

    if not rows or not columns:
        return VisualizationSpec(kind="table")

    requested = _requested_visualization(question)
    if requested == "table":
        return VisualizationSpec(kind="table")

    if len(rows) == 1 and len(columns) == 1 and _is_numeric_column(latest, 0):
        return VisualizationSpec(kind="metric", y=columns[0])

    numeric_indices = [
        index for index in range(len(columns)) if _is_numeric_column(latest, index)
    ]
    temporal = _temporal_column(columns)

    if requested in ("bar", "line") and len(rows) > 1 and numeric_indices:
        y_index = numeric_indices[-1]
        y = columns[y_index]
        if temporal is not None:
            x = temporal
        else:
            x = next(
                (column for index, column in enumerate(columns) if index != y_index),
                None,
            )

        if x is not None:
            return VisualizationSpec(
                kind=requested,
                x=x,
                y=y,
                series=_series_column(columns, x=x, y=y),
            )

    line_requested = any(
        term in question_lower
        for term in ("tendência", "tendencia", "evolução", "evolucao", "linha")
    )
    if temporal and numeric_indices and (line_requested or len(rows) > 1):
        y_index = numeric_indices[-1]
        series = _series_column(
            columns,
            x=temporal,
            y=columns[y_index],
        )
        return VisualizationSpec(
            kind="line",
            x=temporal,
            y=columns[y_index],
            series=series,
        )

    if len(rows) > 1 and numeric_indices:
        y_index = numeric_indices[-1]
        x_index = next(
            (index for index in range(len(columns)) if index != y_index),
            None,
        )
        if x_index is not None:
            return VisualizationSpec(
                kind="bar",
                x=columns[x_index],
                y=columns[y_index],
            )

    return VisualizationSpec(kind="table")
