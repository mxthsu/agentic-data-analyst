from pathlib import Path

import pytest
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import ValidationError

from data_analyst.agent.model_provider import create_chat_model
from data_analyst.config import Settings


def test_carrega_configuracao_gemini_por_variaveis_de_ambiente(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", "data/teste.db")
    monkeypatch.setenv("GOOGLE_API_KEY", "chave-de-teste")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_REQUESTS_PER_MINUTE", "5")
    monkeypatch.setenv("GEMINI_MAX_BURST_REQUESTS", "4")
    monkeypatch.setenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "25")
    monkeypatch.setenv("GEMINI_MAX_OUTPUT_TOKENS", "768")

    settings = Settings(_env_file=None)

    assert settings.database_path == Path("data/teste.db")
    assert settings.google_api_key.get_secret_value() == "chave-de-teste"
    assert settings.gemini_model == "gemini-3.5-flash-lite"
    assert settings.gemini_requests_per_minute == 5
    assert settings.gemini_max_burst_requests == 4
    assert settings.gemini_request_timeout_seconds == 25
    assert settings.gemini_max_output_tokens == 768


def test_modelo_padrao_e_flash_lite(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "chave-de-teste")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.gemini_model == "gemini-3.5-flash-lite"


@pytest.mark.parametrize(
    ("key", "rpm", "timeout", "tokens"),
    [
        ("", "6", "30", "1024"),
        ("chave", "0", "30", "1024"),
        ("chave", "6", "0", "1024"),
        ("chave", "6", "30", "64"),
    ],
)
def test_rejeita_configuracao_invalida(
    monkeypatch,
    key: str,
    rpm: str,
    timeout: str,
    tokens: str,
) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", key)
    monkeypatch.setenv("GEMINI_REQUESTS_PER_MINUTE", rpm)
    monkeypatch.setenv("GEMINI_REQUEST_TIMEOUT_SECONDS", timeout)
    monkeypatch.setenv("GEMINI_MAX_OUTPUT_TOKENS", tokens)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_cria_modelo_gemini_sem_realizar_chamada(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "chave-de-teste")
    settings = Settings(_env_file=None)

    model = create_chat_model(settings)

    assert isinstance(model, ChatGoogleGenerativeAI)
    assert model.model == "gemini-3.5-flash-lite"
    assert model.max_retries == 1
    assert model.timeout == 30
    assert model.max_output_tokens == 1024
    assert isinstance(model.rate_limiter, InMemoryRateLimiter)
    assert model.rate_limiter.requests_per_second == pytest.approx(0.1)
    assert model.rate_limiter.max_bucket_size == 3
    assert model.rate_limiter.available_tokens == pytest.approx(3)
