from __future__ import annotations

import re
import unicodedata
from typing import Literal

from data_analyst.agent.models import TraceEvent
from data_analyst.agent.state import AgentState

_MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _month_in_question(question: str) -> tuple[str, int] | None:
    normalized = _normalize(question)
    for name, number in _MONTHS.items():
        if re.search(rf"\b{name}\b", normalized):
            return name, number
    return None


def _with_trace(
    state: AgentState,
    updates: dict,
    *,
    status: Literal["ok", "esclarecimento"] = "ok",
    detail: str,
) -> dict:
    trace = list(state.get("trace", []))
    trace.append(
        TraceEvent(
            node="resolve_temporal_context",
            status=status,
            detail=detail,
        )
    )
    return {**updates, "trace": trace}


def resolve_temporal_context(state: AgentState) -> dict:
    question = state["question"]
    intent = state["intent"]
    assumptions = list(state.get("assumptions", []))
    updates: dict = {
        "assumptions": assumptions,
        "clarification_question": None,
    }

    normalized = _normalize(question)
    relative_period = "ultimo ano" in normalized or "ultimos 12 meses" in normalized
    if relative_period:
        policy = (
            "Períodos relativos são ancorados na maior data disponível "
            "da fonte relevante, e não na data atual."
        )
        if policy not in assumptions:
            assumptions.append(policy)

        updates["intent"] = intent.model_copy(
            update={
                "temporal_expression": (
                    "últimos 12 meses-calendário ancorados na maior data disponível "
                    "da fonte relevante; início no primeiro dia do mês 11 meses antes "
                    "e fim na maior data disponível"
                )
            }
        )

    month = _month_in_question(question)
    has_explicit_year = bool(re.search(r"\b(?:19|20)\d{2}\b", question))
    if month is None or has_explicit_year:
        detail = (
            "Política de período relativo registrada."
            if relative_period
            else "Nenhum ajuste temporal necessário."
        )
        return _with_trace(state, updates, detail=detail)

    month_name, month_number = month
    years: set[int] = set()
    for coverage in state["schema"].date_coverage.values():
        years.update(coverage.years_by_month.get(month_number, ()))

    if len(years) == 1:
        year = next(iter(years))
        assumption = (
            f'"{month_name}" foi interpretado como {month_name} de {year} '
            "com base na cobertura temporal disponível."
        )
        assumptions.append(assumption)
        updates["intent"] = intent.model_copy(
            update={"temporal_expression": f"{month_name} de {year}"}
        )
        return _with_trace(state, updates, detail=assumption)

    if len(years) > 1:
        available = ", ".join(str(year) for year in sorted(years))
        question_text = (
            f"Qual ano deve ser considerado para {month_name}? "
            f"Há dados disponíveis em {available}."
        )
        updates["clarification_question"] = question_text
        updates["intent"] = intent.model_copy(update={"ambiguity": question_text})
        return _with_trace(
            state,
            updates,
            status="esclarecimento",
            detail=question_text,
        )

    return _with_trace(
        state,
        updates,
        detail=f"Não há cobertura temporal disponível para {month_name}.",
    )
