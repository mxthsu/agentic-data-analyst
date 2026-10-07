from fastapi.testclient import TestClient

from data_analyst.agent.models import (
    AnswerPayload,
    QueryEvidence,
    QueryResult,
    TraceEvent,
    VisualizationSpec,
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


class FailingService:
    def ask(self, _question: str):
        raise RuntimeError("falha interna")


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


def test_ask_nao_expoe_erro_interno() -> None:
    client = TestClient(create_app(FailingService()))

    response = client.post("/ask", json={"question": "Quantos clientes existem?"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Falha ao processar a pergunta."}
