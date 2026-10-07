from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(frozen=True)


class ColumnInfo(Model):
    name: str
    data_type: str
    not_null: bool = False
    primary_key: bool = False


class ForeignKeyInfo(Model):
    column: str
    referenced_table: str
    referenced_column: str


class DateCoverage(Model):
    min_date: str | None = None
    max_date: str | None = None
    years_by_month: dict[int, tuple[int, ...]] = Field(default_factory=dict)


class TableSchema(Model):
    name: str
    columns: tuple[ColumnInfo, ...]
    foreign_keys: tuple[ForeignKeyInfo, ...] = ()


class DatabaseSchema(Model):
    tables: dict[str, TableSchema]
    date_coverage: dict[str, DateCoverage] = Field(default_factory=dict)


class QuestionIntent(Model):
    objective: str
    metric: str | None = None
    dimensions: tuple[str, ...] = ()
    filters: tuple[str, ...] = ()
    temporal_expression: str | None = None
    ambiguity: str | None = None


class InvestigationPlan(Model):
    steps: tuple[str, ...]
    expected_evidence: tuple[str, ...] = ()


class SQLProposal(Model):
    sql: str
    purpose: str


class QueryResult(Model):
    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    truncated: bool = False
    duration_ms: float = 0


class QueryEvidence(Model):
    purpose: str
    sql: str
    result: QueryResult


class EvidenceAssessment(Model):
    decision: Literal["sufficient", "more_data", "clarify"]
    summary: str
    next_query_goal: str | None = None
    clarification_question: str | None = None


class AnswerDraft(Model):
    answer: str
    assumptions: tuple[str, ...] = ()


class AnswerPayload(Model):
    status: Literal["ok", "clarification", "error"]
    answer: str
    assumptions: tuple[str, ...] = ()


class TraceEvent(Model):
    node: str
    status: Literal["ok", "erro", "reparo", "esclarecimento"]
    duration_ms: float | None = None
    sql: str | None = None
    row_count: int | None = None
    detail: str | None = None


class VisualizationSpec(Model):
    kind: Literal["metric", "table", "bar", "line"] = "table"
    x: str | None = None
    y: str | None = None
