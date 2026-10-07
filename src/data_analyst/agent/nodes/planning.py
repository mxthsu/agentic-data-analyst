from __future__ import annotations

import json
import time
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from data_analyst.agent.models import InvestigationPlan, QuestionIntent, TraceEvent
from data_analyst.agent.prompts import INTERPRET_QUESTION_PROMPT, PLAN_INVESTIGATION_PROMPT
from data_analyst.agent.state import AgentState


def _schema_payload(state: AgentState) -> dict[str, Any]:
    schema = state["schema"]
    return {
        name: {
            "columns": [column.name for column in table.columns],
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
    }


def _invoke_structured(model: BaseChatModel, schema: type[BaseModel], messages: list):
    result = model.with_structured_output(schema).invoke(messages)
    return result if isinstance(result, schema) else schema.model_validate(result)


def interpret_question(state: AgentState, model: BaseChatModel) -> dict:
    started = time.perf_counter()
    payload = {"question": state["question"], "schema": _schema_payload(state)}
    intent = _invoke_structured(
        model,
        QuestionIntent,
        [
            SystemMessage(content=INTERPRET_QUESTION_PROMPT),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ],
    )
    trace = list(state.get("trace", []))
    trace.append(
        TraceEvent(
            node="interpret_question",
            status="ok",
            duration_ms=(time.perf_counter() - started) * 1000,
            detail="Intenção estruturada.",
        )
    )
    return {
        "intent": intent,
        "trace": trace,
        "graph_steps": state.get("graph_steps", 0) + 1,
    }


def plan_investigation(state: AgentState, model: BaseChatModel) -> dict:
    started = time.perf_counter()
    payload = {
        "question": state["question"],
        "intent": state["intent"].model_dump(),
        "schema": _schema_payload(state),
    }
    plan = _invoke_structured(
        model,
        InvestigationPlan,
        [
            SystemMessage(content=PLAN_INVESTIGATION_PROMPT),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ],
    )
    trace = list(state.get("trace", []))
    trace.append(
        TraceEvent(
            node="plan_investigation",
            status="ok",
            duration_ms=(time.perf_counter() - started) * 1000,
            detail=f"{len(plan.steps)} passos planejados.",
        )
    )
    return {
        "plan": plan,
        "trace": trace,
        "graph_steps": state.get("graph_steps", 0) + 1,
    }
