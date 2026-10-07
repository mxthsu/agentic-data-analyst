from __future__ import annotations

import json
import time

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from data_analyst.agent.context import evidence_payload
from data_analyst.agent.llm import invoke_structured
from data_analyst.agent.models import AnswerDraft, AnswerPayload, TraceEvent
from data_analyst.agent.prompts import SYNTHESIZE_ANSWER_PROMPT
from data_analyst.agent.state import AgentState


def synthesize_answer(state: AgentState, model: BaseChatModel) -> dict:
    started = time.perf_counter()
    payload = {
        "question": state["question"],
        "intent": state["intent"].model_dump(),
        "evidence": evidence_payload(state.get("evidence", [])),
        "assumptions": state.get("assumptions", []),
    }
    draft = invoke_structured(
        model,
        AnswerDraft,
        [
            SystemMessage(content=SYNTHESIZE_ANSWER_PROMPT),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False, default=str)),
        ],
    )
    assumptions = tuple(
        dict.fromkeys(
            [*state.get("assumptions", []), *draft.assumptions]
        )
    )
    answer = AnswerPayload(
        status="ok",
        answer=draft.answer,
        assumptions=assumptions,
    )
    trace = list(state.get("trace", []))
    trace.append(
        TraceEvent(
            node="synthesize_answer",
            status="ok",
            duration_ms=(time.perf_counter() - started) * 1000,
            detail="Resposta produzida a partir das evidências.",
        )
    )
    return {
        "final_answer": answer,
        "trace": trace,
        "graph_steps": state.get("graph_steps", 0) + 1,
    }


def request_clarification(state: AgentState) -> dict:
    assessment = state.get("assessment")
    question = state.get("clarification_question")
    if not question:
        question = (
            assessment.clarification_question
            if assessment and assessment.clarification_question
            else "Preciso de mais detalhes para responder com segurança."
        )
    trace = list(state.get("trace", []))
    trace.append(
        TraceEvent(
            node="request_clarification",
            status="esclarecimento",
            detail=question,
        )
    )
    return {
        "final_answer": AnswerPayload(
            status="clarification",
            answer=question,
            assumptions=tuple(state.get("assumptions", [])),
        ),
        "trace": trace,
        "graph_steps": state.get("graph_steps", 0) + 1,
    }


def fail_gracefully(state: AgentState) -> dict:
    error = state.get("last_error") or "Limite de execução atingido."
    trace = list(state.get("trace", []))
    trace.append(
        TraceEvent(
            node="fail_gracefully",
            status="erro",
            detail=error,
        )
    )
    return {
        "final_answer": AnswerPayload(
            status="error",
            answer="Não foi possível concluir a análise dentro dos limites definidos.",
            assumptions=tuple(state.get("assumptions", [])),
        ),
        "trace": trace,
    }
