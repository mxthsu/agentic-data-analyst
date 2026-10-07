from __future__ import annotations

import json
import time

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from data_analyst.agent.context import schema_payload
from data_analyst.agent.llm import invoke_structured
from data_analyst.agent.models import InvestigationPlan, QuestionIntent, TraceEvent
from data_analyst.agent.prompts import INTERPRET_QUESTION_PROMPT, PLAN_INVESTIGATION_PROMPT
from data_analyst.agent.state import AgentState


def interpret_question(state: AgentState, model: BaseChatModel) -> dict:
    started = time.perf_counter()
    payload = {
        "question": state["question"],
        "schema": schema_payload(state["schema"]),
    }
    intent = invoke_structured(
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
        "schema": schema_payload(state["schema"]),
    }
    plan = invoke_structured(
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
