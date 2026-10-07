from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

from data_analyst.config import Settings
from data_analyst.service import DataAnalystService


def _load_settings() -> Settings | None:
    try:
        return Settings()
    except ValidationError:
        return None


SETTINGS = _load_settings()
RUN_E2E = os.getenv("RUN_E2E") == "1"

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not RUN_E2E or SETTINGS is None or not SETTINGS.database_path.exists(),
        reason="E2E real exige RUN_E2E=1, banco local e configuração do Gemini",
    ),
]


def test_modelo_real_responde_reclamacoes_nao_resolvidas_por_canal() -> None:
    assert SETTINGS is not None

    service = DataAnalystService.from_settings(SETTINGS)
    state = service.ask("Qual o número de reclamações não resolvidas por canal?")

    assert state["final_answer"].status == "ok"
    assert state.get("evidence")

    evidence_text = repr(
        [
            (item.result.columns, item.result.rows)
            for item in state["evidence"]
        ]
    )
    for expected in ("Telefone", "Chat", "E-mail", "19", "18", "14"):
        assert expected in evidence_text
