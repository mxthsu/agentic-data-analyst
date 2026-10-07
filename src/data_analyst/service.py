from __future__ import annotations

from pathlib import Path
from typing import cast
from uuid import uuid4

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.language_models import BaseChatModel

from data_analyst.agent.graph import build_graph
from data_analyst.agent.model_provider import create_chat_model
from data_analyst.agent.models import TokenUsage
from data_analyst.agent.state import AgentState
from data_analyst.config import Settings


def _aggregate_token_usage(usage_metadata: dict) -> TokenUsage:
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0

    for usage in usage_metadata.values():
        current_input = int(usage.get("input_tokens", 0) or 0)
        current_output = int(usage.get("output_tokens", 0) or 0)
        current_total = usage.get("total_tokens")
        input_tokens += current_input
        output_tokens += current_output
        total_tokens += int(
            current_total
            if current_total is not None
            else current_input + current_output
        )

    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


class DataAnalystService:
    def __init__(self, db_path: Path, model: BaseChatModel):
        self._graph = build_graph(db_path, model)

    @classmethod
    def from_settings(cls, settings: Settings) -> DataAnalystService:
        return cls(
            db_path=settings.database_path,
            model=create_chat_model(settings),
        )

    def ask(self, question: str) -> AgentState:
        normalized = question.strip()
        if not normalized:
            raise ValueError("A pergunta não pode estar vazia.")

        with get_usage_metadata_callback() as usage_callback:
            result = self._graph.invoke(
                {
                    "question": normalized,
                    "trace_id": uuid4().hex,
                }
            )

        result["token_usage"] = _aggregate_token_usage(
            usage_callback.usage_metadata
        )
        return cast(AgentState, result)
