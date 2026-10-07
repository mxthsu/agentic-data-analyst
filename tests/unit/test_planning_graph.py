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
            INSERT INTO clientes VALUES (1, 'SC'), (2, 'SP');
            INSERT INTO compras VALUES
                (1, 1, '2025-05-10', 'App'),
                (2, 2, '2025-05-12', 'App');
            """
        )


def test_grafo_descobre_planeja_consulta_e_responde(tmp_path: Path) -> None:
    db_path = tmp_path / "dados.db"
    _database(db_path)
    model = ScriptedModel(
        QuestionIntent(
            objective="contar clientes por estado",
            metric="clientes distintos",
            dimensions=("estado",),
            filters=("canal=App",),
            temporal_expression="maio de 2025",
        ),
        InvestigationPlan(
            steps=("agrupar clientes distintos por estado",),
            expected_evidence=("ranking por estado",),
        ),
        SQLProposal(
            sql="""
                SELECT c.estado, COUNT(DISTINCT c.id) AS clientes
                FROM clientes c
                JOIN compras p ON p.cliente_id = c.id
                WHERE p.canal = 'App'
                  AND strftime('%Y-%m', p.data_compra) = '2025-05'
                GROUP BY c.estado
                ORDER BY clientes DESC, c.estado
            """,
            purpose="rankear clientes distintos por estado",
        ),
        EvidenceAssessment(
            decision="sufficient",
            summary="O ranking solicitado foi obtido.",
        ),
        AnswerDraft(
            answer="SC e SP possuem 1 cliente cada no recorte.",
        ),
    )

    result = build_graph(db_path, model).invoke(
        {"question": "Quais estados tiveram mais clientes via App em maio de 2025?"}
    )

    assert result["final_answer"].status == "ok"
    assert result["query_count"] == 1
    assert len(result["evidence"]) == 1
    assert result["evidence"][0].result.rows == (("SC", 1), ("SP", 1))
    assert result["graph_steps"] == 8
    assert result["visualization"].kind == "bar"
    assert result["visualization"].x == "estado"
    assert result["visualization"].y == "clientes"
    assert [event.node for event in result["trace"]] == [
        "discover_schema",
        "interpret_question",
        "resolve_temporal_context",
        "plan_investigation",
        "generate_sql",
        "validate_sql",
        "execute_sql",
        "assess_evidence",
        "synthesize_answer",
        "select_visualization",
    ]
