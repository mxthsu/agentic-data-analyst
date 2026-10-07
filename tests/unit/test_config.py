from pathlib import Path

import pytest
from pydantic import ValidationError

from data_analyst.agent.model_provider import create_chat_model
from data_analyst.config import Settings


def test_carrega_configuracao_por_variaveis_de_ambiente(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", "data/teste.db")
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-de-teste")
    monkeypatch.setenv("OPENROUTER_MODEL", "provedor/modelo")

    settings = Settings(_env_file=None)

    assert settings.database_path == Path("data/teste.db")
    assert settings.openrouter_model == "provedor/modelo"
    assert settings.openrouter_api_key.get_secret_value() == "chave-de-teste"


@pytest.mark.parametrize(
    ("key", "model"),
    [
        ("", "provedor/modelo"),
        ("chave-de-teste", ""),
        ("chave-de-teste", "   "),
    ],
)
def test_rejeita_configuracao_incompleta(monkeypatch, key: str, model: str) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", key)
    monkeypatch.setenv("OPENROUTER_MODEL", model)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_cria_modelo_openrouter_sem_realizar_chamada(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-de-teste")
    monkeypatch.setenv("OPENROUTER_MODEL", "provedor/modelo")
    settings = Settings(_env_file=None)

    model = create_chat_model(settings)

    assert model.model_name == "provedor/modelo"
    assert model.temperature == 0
    assert model.max_retries == 2
