from __future__ import annotations

from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from data_analyst.agent.nodes.discovery import discover_schema
from data_analyst.agent.nodes.planning import interpret_question, plan_investigation
from data_analyst.agent.nodes.presentation import select_visualization
from data_analyst.agent.nodes.query import (
    assess_evidence,
    execute_sql,
    generate_sql,
    validate_sql,
)
from data_analyst.agent.nodes.recovery import repair_sql
from data_analyst.agent.nodes.synthesis import (
    fail_gracefully,
    request_clarification,
    synthesize_answer,
)
from data_analyst.agent.nodes.temporal import resolve_temporal_context
from data_analyst.agent.state import AgentState
from data_analyst.safety.sql_guard import SQLGuard

MAX_QUERIES = 4
MAX_SQL_REPAIRS = 2
MAX_GRAPH_STEPS = 12


def _budget_exhausted(state: AgentState) -> bool:
    return state.get("graph_steps", 0) >= MAX_GRAPH_STEPS


def _after_temporal_resolution(state: AgentState) -> str:
    return "clarify" if state.get("clarification_question") else "plan"


def _after_validation(state: AgentState) -> str:
    if state.get("last_error"):
        if state.get("repair_count", 0) < MAX_SQL_REPAIRS and not _budget_exhausted(state):
            return "repair"
        return "fail"
    if state.get("query_count", 0) >= MAX_QUERIES or _budget_exhausted(state):
        return "fail"
    return "execute"


def _after_execution(state: AgentState) -> str:
    if state.get("last_error"):
        can_repair = (
            state.get("repair_count", 0) < MAX_SQL_REPAIRS
            and state.get("query_count", 0) < MAX_QUERIES
            and not _budget_exhausted(state)
        )
        return "repair" if can_repair else "fail"
    return "assess" if not _budget_exhausted(state) else "fail"


def _after_assessment(state: AgentState) -> str:
    assessment = state.get("assessment")
    if assessment is None:
        return "fail"
    if assessment.decision == "sufficient":
        return "synthesize" if not _budget_exhausted(state) else "fail"
    if assessment.decision == "clarify":
        return "clarify" if not _budget_exhausted(state) else "fail"
    if (
        state.get("query_count", 0) >= MAX_QUERIES
        or _budget_exhausted(state)
    ):
        return "fail"
    return "generate"


def build_graph(
    db_path: Path,
    model: BaseChatModel,
    *,
    guard: SQLGuard | None = None,
):
    active_guard = guard or SQLGuard()
    graph = StateGraph(AgentState)

    graph.add_node("discover_schema", lambda state: discover_schema(state, db_path))
    graph.add_node("interpret_question", lambda state: interpret_question(state, model))
    graph.add_node("resolve_temporal_context", resolve_temporal_context)
    graph.add_node("plan_investigation", lambda state: plan_investigation(state, model))
    graph.add_node("generate_sql", lambda state: generate_sql(state, model))
    graph.add_node("validate_sql", lambda state: validate_sql(state, active_guard))
    graph.add_node("execute_sql", lambda state: execute_sql(state, db_path, active_guard))
    graph.add_node("assess_evidence", lambda state: assess_evidence(state, model))
    graph.add_node("repair_sql", lambda state: repair_sql(state, model))
    graph.add_node("synthesize_answer", lambda state: synthesize_answer(state, model))
    graph.add_node("select_visualization", select_visualization)
    graph.add_node("request_clarification", request_clarification)
    graph.add_node("fail_gracefully", fail_gracefully)

    graph.add_edge(START, "discover_schema")
    graph.add_edge("discover_schema", "interpret_question")
    graph.add_edge("interpret_question", "resolve_temporal_context")
    graph.add_conditional_edges(
        "resolve_temporal_context",
        _after_temporal_resolution,
        {
            "plan": "plan_investigation",
            "clarify": "request_clarification",
        },
    )
    graph.add_edge("plan_investigation", "generate_sql")
    graph.add_edge("generate_sql", "validate_sql")
    graph.add_conditional_edges(
        "validate_sql",
        _after_validation,
        {
            "execute": "execute_sql",
            "repair": "repair_sql",
            "fail": "fail_gracefully",
        },
    )
    graph.add_conditional_edges(
        "execute_sql",
        _after_execution,
        {
            "assess": "assess_evidence",
            "repair": "repair_sql",
            "fail": "fail_gracefully",
        },
    )
    graph.add_edge("repair_sql", "validate_sql")
    graph.add_conditional_edges(
        "assess_evidence",
        _after_assessment,
        {
            "generate": "generate_sql",
            "synthesize": "synthesize_answer",
            "clarify": "request_clarification",
            "fail": "fail_gracefully",
        },
    )
    graph.add_edge("synthesize_answer", "select_visualization")
    graph.add_edge("select_visualization", END)
    graph.add_edge("request_clarification", END)
    graph.add_edge("fail_gracefully", END)

    return graph.compile()
