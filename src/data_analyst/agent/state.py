from __future__ import annotations

from typing import Required, TypedDict

from .models import (
    AnswerPayload,
    DatabaseSchema,
    EvidenceAssessment,
    InvestigationPlan,
    QueryEvidence,
    QuestionIntent,
    TokenUsage,
    TraceEvent,
    VisualizationSpec,
)


class AgentState(TypedDict, total=False):
    question: Required[str]
    trace_id: str
    schema: DatabaseSchema
    intent: QuestionIntent
    plan: InvestigationPlan
    current_sql: str | None
    current_query_purpose: str | None
    last_error: str | None
    assessment: EvidenceAssessment | None
    clarification_question: str | None
    query_count: int
    repair_count: int
    graph_steps: int
    evidence: list[QueryEvidence]
    errors: list[str]
    assumptions: list[str]
    token_usage: TokenUsage
    trace: list[TraceEvent]
    final_answer: AnswerPayload | None
    visualization: VisualizationSpec | None
