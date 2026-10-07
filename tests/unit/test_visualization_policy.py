from data_analyst.agent.models import QueryEvidence, QueryResult
from data_analyst.visualization.policy import choose_visualization


def _evidence(columns, rows) -> list[QueryEvidence]:
    return [
        QueryEvidence(
            purpose="teste",
            sql="SELECT ...",
            result=QueryResult(columns=columns, rows=rows),
        )
    ]


def test_escolhe_indicador_para_valor_unico() -> None:
    spec = choose_visualization(
        "Quantos clientes interagiram?",
        _evidence(("clientes",), ((17,),)),
    )

    assert spec.kind == "metric"
    assert spec.y == "clientes"


def test_escolhe_barras_para_comparacao_categorica() -> None:
    spec = choose_visualization(
        "Quais categorias tiveram maior média?",
        _evidence(
            ("categoria", "media"),
            (("Roupas", 2.211), ("Viagens", 2.162)),
        ),
    )

    assert spec.kind == "bar"
    assert spec.x == "categoria"
    assert spec.y == "media"


def test_escolhe_linha_para_tendencia_com_serie() -> None:
    spec = choose_visualization(
        "Qual a tendência de reclamações por canal no último ano?",
        _evidence(
            ("mes", "canal", "total"),
            (
                ("2025-01", "Chat", 4),
                ("2025-01", "Telefone", 2),
                ("2025-02", "Chat", 6),
            ),
        ),
    )

    assert spec.kind == "line"
    assert spec.x == "mes"
    assert spec.y == "total"
    assert spec.series == "canal"


def test_respeita_pedido_explicito_de_tabela() -> None:
    spec = choose_visualization(
        "Mostre em tabela os resultados por estado.",
        _evidence(("estado", "clientes"), (("SC", 3), ("SP", 5))),
    )

    assert spec.kind == "table"


def test_respeita_pedido_explicito_de_barras_em_resultado_temporal() -> None:
    spec = choose_visualization(
        "Mostre a tendência de reclamações em um gráfico de barras.",
        _evidence(
            ("mes", "canal", "total"),
            (
                ("2025-01", "Chat", 4),
                ("2025-01", "Telefone", 2),
                ("2025-02", "Chat", 6),
            ),
        ),
    )

    assert spec.kind == "bar"
    assert spec.x == "mes"
    assert spec.y == "total"
    assert spec.series == "canal"


def test_respeita_pedido_explicito_de_linha_em_comparacao_categorica() -> None:
    spec = choose_visualization(
        "Mostre os clientes por estado em um gráfico de linha.",
        _evidence(
            ("estado", "clientes"),
            (("SC", 3), ("SP", 5)),
        ),
    )

    assert spec.kind == "line"
    assert spec.x == "estado"
    assert spec.y == "clientes"
    assert spec.series is None
