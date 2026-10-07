from __future__ import annotations

from typing import Required, TypedDict

from .models import (
    DatabaseSchema,
    InvestigationPlan,
    QueryResult,
    QuestionIntent,
    TraceEvent,
    VisualizationSpec,
)


class AgentState(TypedDict, total=False):
    question: Required[str]
    schema: DatabaseSchema
    intent: QuestionIntent
    plan: InvestigationPlan
    current_sql: str | None
    query_count: int
    repair_count: int
    graph_steps: int
    query_results: list[QueryResult]
    errors: list[str]
    assumptions: list[str]
    trace: list[TraceEvent]
    final_answer: str | None
    visualization: VisualizationSpec | None
