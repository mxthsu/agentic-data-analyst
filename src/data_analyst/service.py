from __future__ import annotations

from pathlib import Path
from typing import cast
from uuid import uuid4

from langchain_core.language_models import BaseChatModel

from data_analyst.agent.graph import build_graph
from data_analyst.agent.model_provider import create_chat_model
from data_analyst.agent.state import AgentState
from data_analyst.config import Settings


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

        result = self._graph.invoke(
            {
                "question": normalized,
                "trace_id": uuid4().hex,
            }
        )
        return cast(AgentState, result)
