from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from data_analyst.agent.models import QueryResult, TraceEvent, VisualizationSpec
from data_analyst.agent.state import AgentState


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class AskResponse(BaseModel):
    trace_id: str
    status: Literal["ok", "clarification", "error"]
    answer: str
    assumptions: tuple[str, ...] = ()
    result: QueryResult | None = None
    visualization: VisualizationSpec | None = None
    trace: tuple[TraceEvent, ...] = ()

    @classmethod
    def from_state(cls, state: AgentState) -> AskResponse:
        answer = state.get("final_answer")
        if answer is None:
            raise ValueError("O agente não produziu uma resposta final.")

        evidence = state.get("evidence", [])
        latest_result = evidence[-1].result if evidence else None
        return cls(
            trace_id=state.get("trace_id", ""),
            status=answer.status,
            answer=answer.answer,
            assumptions=answer.assumptions,
            result=latest_result,
            visualization=state.get("visualization"),
            trace=tuple(state.get("trace", [])),
        )


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
