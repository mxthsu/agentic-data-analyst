from __future__ import annotations

import json
import time

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from data_analyst.agent.context import schema_payload
from data_analyst.agent.llm import invoke_structured
from data_analyst.agent.models import SQLProposal, TraceEvent
from data_analyst.agent.prompts import REPAIR_SQL_PROMPT
from data_analyst.agent.state import AgentState


def repair_sql(state: AgentState, model: BaseChatModel) -> dict:
    started = time.perf_counter()
    previous_sql = state.get("current_sql") or ""
    previous_error = state.get("last_error") or "Erro não informado."
    payload = {
        "question": state["question"],
        "query_purpose": state.get("current_query_purpose"),
        "sql": previous_sql,
        "error": previous_error,
        "schema": schema_payload(state["schema"]),
    }
    proposal = invoke_structured(
        model,
        SQLProposal,
        [
            SystemMessage(content=REPAIR_SQL_PROMPT),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ],
    )
    trace = list(state.get("trace", []))
    trace.append(
        TraceEvent(
            node="repair_sql",
            status="reparo",
            duration_ms=(time.perf_counter() - started) * 1000,
            sql=proposal.sql,
            detail=f"Consulta reparada após: {previous_error}",
        )
    )
    return {
        "current_sql": proposal.sql,
        "current_query_purpose": proposal.purpose,
        "repair_count": state.get("repair_count", 0) + 1,
        "last_error": None,
        "trace": trace,
        "graph_steps": state.get("graph_steps", 0) + 1,
    }
