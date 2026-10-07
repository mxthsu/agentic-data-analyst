from __future__ import annotations

import json
import time
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from data_analyst.agent.context import evidence_payload, schema_payload
from data_analyst.agent.llm import invoke_structured
from data_analyst.agent.models import (
    EvidenceAssessment,
    QueryEvidence,
    SQLProposal,
    TraceEvent,
)
from data_analyst.agent.prompts import ASSESS_EVIDENCE_PROMPT, GENERATE_SQL_PROMPT
from data_analyst.agent.state import AgentState
from data_analyst.database.executor import QueryExecutionError, execute_query
from data_analyst.safety.sql_guard import SQLGuard


def generate_sql(state: AgentState, model: BaseChatModel) -> dict:
    started = time.perf_counter()
    assessment = state.get("assessment")
    payload = {
        "question": state["question"],
        "intent": state["intent"].model_dump(),
        "plan": state["plan"].model_dump(),
        "schema": schema_payload(state["schema"]),
        "evidence": evidence_payload(state.get("evidence", [])),
        "next_query_goal": assessment.next_query_goal if assessment else None,
    }
    proposal = invoke_structured(
        model,
        SQLProposal,
        [
            SystemMessage(content=GENERATE_SQL_PROMPT),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False, default=str)),
        ],
    )
    trace = list(state.get("trace", []))
    trace.append(
        TraceEvent(
            node="generate_sql",
            status="ok",
            duration_ms=(time.perf_counter() - started) * 1000,
            sql=proposal.sql,
            detail=proposal.purpose,
        )
    )
    return {
        "current_sql": proposal.sql,
        "current_query_purpose": proposal.purpose,
        "last_error": None,
        "trace": trace,
        "graph_steps": state.get("graph_steps", 0) + 1,
    }


def validate_sql(state: AgentState, guard: SQLGuard) -> dict:
    started = time.perf_counter()
    sql = state.get("current_sql") or ""
    validation = guard.validate(sql)
    trace = list(state.get("trace", []))
    trace.append(
        TraceEvent(
            node="validate_sql",
            status="ok" if validation.valid else "erro",
            duration_ms=(time.perf_counter() - started) * 1000,
            sql=sql,
            detail=validation.reason,
        )
    )
    return {
        "last_error": None if validation.valid else validation.reason,
        "trace": trace,
        "graph_steps": state.get("graph_steps", 0) + 1,
    }


def execute_sql(state: AgentState, db_path: Path, guard: SQLGuard) -> dict:
    started = time.perf_counter()
    sql = state.get("current_sql") or ""
    purpose = state.get("current_query_purpose") or "consulta sem descrição"
    query_count = state.get("query_count", 0) + 1
    trace = list(state.get("trace", []))

    try:
        result = execute_query(db_path, sql, guard=guard)
    except QueryExecutionError as exc:
        error = str(exc)
        errors = [*state.get("errors", []), error]
        trace.append(
            TraceEvent(
                node="execute_sql",
                status="erro",
                duration_ms=(time.perf_counter() - started) * 1000,
                sql=sql,
                detail=error,
            )
        )
        return {
            "query_count": query_count,
            "last_error": error,
            "errors": errors,
            "trace": trace,
            "graph_steps": state.get("graph_steps", 0) + 1,
        }

    evidence = [
        *state.get("evidence", []),
        QueryEvidence(purpose=purpose, sql=sql, result=result),
    ]
    trace.append(
        TraceEvent(
            node="execute_sql",
            status="ok",
            duration_ms=(time.perf_counter() - started) * 1000,
            sql=sql,
            row_count=len(result.rows),
            detail="Consulta executada com sucesso.",
        )
    )
    return {
        "query_count": query_count,
        "last_error": None,
        "evidence": evidence,
        "trace": trace,
        "graph_steps": state.get("graph_steps", 0) + 1,
    }


def assess_evidence(state: AgentState, model: BaseChatModel) -> dict:
    started = time.perf_counter()
    payload = {
        "question": state["question"],
        "intent": state["intent"].model_dump(),
        "plan": state["plan"].model_dump(),
        "evidence": evidence_payload(state.get("evidence", [])),
    }
    assessment = invoke_structured(
        model,
        EvidenceAssessment,
        [
            SystemMessage(content=ASSESS_EVIDENCE_PROMPT),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False, default=str)),
        ],
    )
    trace = list(state.get("trace", []))
    trace.append(
        TraceEvent(
            node="assess_evidence",
            status="ok",
            duration_ms=(time.perf_counter() - started) * 1000,
            detail=assessment.summary,
        )
    )
    return {
        "assessment": assessment,
        "trace": trace,
        "graph_steps": state.get("graph_steps", 0) + 1,
    }
