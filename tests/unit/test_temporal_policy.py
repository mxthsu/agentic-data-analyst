from data_analyst.agent.models import DatabaseSchema, DateCoverage, QuestionIntent
from data_analyst.agent.nodes.temporal import resolve_temporal_context


def _state(question: str, years_by_month: dict[int, tuple[int, ...]]):
    return {
        "question": question,
        "intent": QuestionIntent(
            objective="analisar compras",
            temporal_expression="maio" if "maio" in question.lower() else "último ano",
        ),
        "schema": DatabaseSchema(
            tables={},
            date_coverage={
                "compras.data_compra": DateCoverage(
                    years_by_month=years_by_month,
                )
            },
        ),
        "trace": [],
    }


def test_inferir_ano_quando_mes_tem_um_unico_ano_disponivel() -> None:
    result = resolve_temporal_context(_state("Compras via App em maio", {5: (2025,)}))

    assert result["intent"].temporal_expression == "maio de 2025"
    assert result["clarification_question"] is None
    assert "maio de 2025" in result["assumptions"][0]
    assert result["trace"][-1].node == "resolve_temporal_context"


def test_pedir_esclarecimento_quando_mes_tem_mais_de_um_ano() -> None:
    result = resolve_temporal_context(
        _state("Compras via App em maio", {5: (2024, 2025)})
    )

    assert result["clarification_question"] is not None
    assert "2024, 2025" in result["clarification_question"]
    assert result["intent"].ambiguity == result["clarification_question"]
    assert result["trace"][-1].status == "esclarecimento"


def test_periodo_relativo_e_ancorado_nos_dados() -> None:
    result = resolve_temporal_context(
        _state("Tendência de reclamações no último ano", {7: (2025,)})
    )

    assert len(result["assumptions"]) == 1
    assert "maior data disponível" in result["assumptions"][0]
    assert result["clarification_question"] is None
