import pytest
from fastapi.testclient import TestClient

from data_analyst.agent.models import (
    AnswerPayload,
    QueryEvidence,
    QueryResult,
    TraceEvent,
    VisualizationSpec,
)
from data_analyst.agent.provider_errors import (
    ModelAuthenticationError,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from data_analyst.api.main import create_app


class FakeService:
    def ask(self, question: str):
        return {
            "question": question,
            "trace_id": "trace-123",
            "final_answer": AnswerPayload(
                status="ok",
                answer="Foram encontrados 17 clientes.",
            ),
            "evidence": [
                QueryEvidence(
                    purpose="contar clientes",
                    sql="SELECT COUNT(*) AS clientes FROM clientes",
                    result=QueryResult(
                        columns=("clientes",),
                        rows=((17,),),
                    ),
                )
            ],
            "visualization": VisualizationSpec(kind="metric", y="clientes"),
            "trace": [
                TraceEvent(
                    node="execute_sql",
                    status="ok",
                    sql="SELECT COUNT(*) AS clientes FROM clientes",
                    row_count=1,
                )
            ],
        }


class ErrorService:
    def __init__(self, error: Exception):
        self.error = error

    def ask(self, _question: str):
        raise self.error


def test_health_nao_depende_de_modelo_configurado() -> None:
    client = TestClient(create_app(FakeService()))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ask_expoe_resposta_resultado_visualizacao_e_trace() -> None:
    client = TestClient(create_app(FakeService()))

    response = client.post("/ask", json={"question": "Quantos clientes existem?"})

    assert response.status_code == 200
    body = response.json()
    assert body["trace_id"] == "trace-123"
    assert body["status"] == "ok"
    assert body["answer"] == "Foram encontrados 17 clientes."
    assert body["result"]["rows"] == [[17]]
    assert body["visualization"] == {
        "kind": "metric",
        "x": None,
        "y": "clientes",
        "series": None,
    }
    assert body["trace"][0]["node"] == "execute_sql"
    assert body["trace"][0]["sql"].startswith("SELECT COUNT")


def test_ask_rejeita_pergunta_curta() -> None:
    client = TestClient(create_app(FakeService()))

    response = client.post("/ask", json={"question": "?"})

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (
            ModelRateLimitError("limite"),
            429,
            (
                "Limite temporário da API Gemini atingido. "
                "Aguarde alguns instantes e tente novamente."
            ),
        ),
        (
            ModelTimeoutError("timeout"),
            504,
            "A API Gemini demorou mais que o limite configurado. Tente novamente.",
        ),
        (
            ModelAuthenticationError("auth"),
            503,
            "A credencial da API Gemini não foi aceita.",
        ),
        (
            ModelUnavailableError("indisponível"),
            503,
            "A API Gemini está temporariamente indisponível.",
        ),
    ],
)
def test_ask_traduz_erros_controlados_do_provider(
    error: Exception,
    status_code: int,
    detail: str,
) -> None:
    client = TestClient(create_app(ErrorService(error)))

    response = client.post("/ask", json={"question": "Quantos clientes existem?"})

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}


def test_ask_nao_expoe_erro_interno() -> None:
    client = TestClient(create_app(ErrorService(RuntimeError("falha interna"))))

    response = client.post("/ask", json={"question": "Quantos clientes existem?"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Falha ao processar a pergunta."}
