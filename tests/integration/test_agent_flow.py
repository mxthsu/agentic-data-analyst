import sqlite3
from pathlib import Path

from data_analyst.agent.graph import build_graph
from data_analyst.agent.models import (
    AnswerDraft,
    EvidenceAssessment,
    InvestigationPlan,
    QuestionIntent,
    SQLProposal,
)
from tests.fakes import ScriptedModel


def _database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE clientes (
                id INTEGER PRIMARY KEY,
                estado TEXT
            );
            CREATE TABLE compras (
                id INTEGER PRIMARY KEY,
                cliente_id INTEGER,
                data_compra TEXT,
                canal TEXT,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            );
            INSERT INTO clientes VALUES (1, 'SC'), (2, 'SP'), (3, 'SC');
            INSERT INTO compras VALUES
                (1, 1, '2025-05-10', 'App'),
                (2, 2, '2025-05-12', 'App'),
                (3, 3, '2025-05-15', 'Site');
            """
        )


def _base_responses() -> tuple[QuestionIntent, InvestigationPlan]:
    return (
        QuestionIntent(
            objective="analisar compras",
            metric="clientes distintos",
            dimensions=("estado",),
        ),
        InvestigationPlan(
            steps=("consultar compras",),
            expected_evidence=("resultado agregado",),
        ),
    )


def test_sql_com_coluna_inexistente_e_reparado_e_reexecutado(tmp_path: Path) -> None:
    db_path = tmp_path / "dados.db"
    _database(db_path)
    intent, plan = _base_responses()
    model = ScriptedModel(
        intent,
        plan,
        SQLProposal(
            sql="SELECT cliente_id_inexistente FROM compras",
            purpose="consultar clientes",
        ),
        SQLProposal(
            sql="SELECT COUNT(DISTINCT cliente_id) AS clientes FROM compras",
            purpose="contar clientes distintos",
        ),
        EvidenceAssessment(
            decision="sufficient",
            summary="A contagem foi obtida após o reparo.",
        ),
        AnswerDraft(status="ok", answer="Foram encontrados 3 clientes."),
    )

    result = build_graph(db_path, model).invoke({"question": "Quantos clientes compraram?"})

    assert result["final_answer"].status == "ok"
    assert result["repair_count"] == 1
    assert result["query_count"] == 2
    assert result["evidence"][0].result.rows == ((3,),)
    nodes = [event.node for event in result["trace"]]
    assert nodes.count("repair_sql") == 1
    assert nodes.count("execute_sql") == 2


def test_operacao_de_escrita_e_bloqueada_antes_da_execucao_e_reparada(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "dados.db"
    _database(db_path)
    intent, plan = _base_responses()
    model = ScriptedModel(
        intent,
        plan,
        SQLProposal(
            sql="DELETE FROM compras",
            purpose="consultar compras",
        ),
        SQLProposal(
            sql="SELECT COUNT(*) AS compras FROM compras",
            purpose="contar compras",
        ),
        EvidenceAssessment(
            decision="sufficient",
            summary="A contagem foi obtida com uma consulta segura.",
        ),
        AnswerDraft(status="ok", answer="Há 3 compras."),
    )

    result = build_graph(db_path, model).invoke({"question": "Quantas compras existem?"})

    assert result["final_answer"].status == "ok"
    assert result["repair_count"] == 1
    assert result["query_count"] == 1
    assert result["evidence"][0].result.rows == ((3,),)
    validation_events = [
        event for event in result["trace"] if event.node == "validate_sql"
    ]
    assert validation_events[0].status == "erro"
    assert validation_events[1].status == "ok"


def test_agente_pode_fazer_mais_de_uma_consulta_antes_de_responder(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "dados.db"
    _database(db_path)
    intent, plan = _base_responses()
    model = ScriptedModel(
        intent,
        plan,
        SQLProposal(
            sql="SELECT COUNT(*) AS compras FROM compras",
            purpose="medir o volume total de compras",
        ),
        EvidenceAssessment(
            decision="more_data",
            summary="Falta a distribuição por estado.",
            next_query_goal="agrupar clientes distintos por estado",
        ),
        SQLProposal(
            sql="""
                SELECT c.estado, COUNT(DISTINCT c.id) AS clientes
                FROM clientes c
                JOIN compras p ON p.cliente_id = c.id
                GROUP BY c.estado
                ORDER BY clientes DESC, c.estado
            """,
            purpose="agrupar clientes por estado",
        ),
        EvidenceAssessment(
            decision="sufficient",
            summary="As duas evidências cobrem a pergunta.",
        ),
        AnswerDraft(
            status="ok",
            answer="Há 3 compras; SC reúne 2 clientes e SP reúne 1.",
        ),
    )

    result = build_graph(db_path, model).invoke(
        {"question": "Quantas compras há e como os clientes se distribuem por estado?"}
    )

    assert result["final_answer"].status == "ok"
    assert result["query_count"] == 2
    assert len(result["evidence"]) == 2
    assert [item.result.rows for item in result["evidence"]] == [
        ((3,),),
        (("SC", 2), ("SP", 1)),
    ]
    nodes = [event.node for event in result["trace"]]
    assert nodes.count("generate_sql") == 2
    assert nodes.count("assess_evidence") == 2


def test_reparos_sao_limitados_e_falha_e_controlada(tmp_path: Path) -> None:
    db_path = tmp_path / "dados.db"
    _database(db_path)
    intent, plan = _base_responses()
    model = ScriptedModel(
        intent,
        plan,
        SQLProposal(sql="DELETE FROM compras", purpose="consultar compras"),
        SQLProposal(sql="DELETE FROM compras", purpose="consultar compras"),
        SQLProposal(sql="DELETE FROM compras", purpose="consultar compras"),
    )

    result = build_graph(db_path, model).invoke({"question": "Quantas compras existem?"})

    assert result["final_answer"].status == "error"
    assert result["repair_count"] == 2
    assert result.get("query_count", 0) == 0
    assert result["graph_steps"] <= 12
    assert [event.node for event in result["trace"]].count("repair_sql") == 2
