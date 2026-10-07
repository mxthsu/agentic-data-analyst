import sqlite3
from pathlib import Path

from data_analyst.agent.graph import build_graph
from data_analyst.agent.models import InvestigationPlan, QuestionIntent


class FakeRunnable:
    def __init__(self, schema):
        self.schema = schema

    def invoke(self, _messages):
        if self.schema is QuestionIntent:
            return QuestionIntent(
                objective="contar clientes por estado",
                metric="clientes distintos",
                dimensions=("estado",),
                filters=("canal=App",),
                temporal_expression="maio",
            )
        if self.schema is InvestigationPlan:
            return InvestigationPlan(
                steps=(
                    "identificar o período de maio disponível",
                    "agrupar clientes distintos por estado",
                ),
                expected_evidence=("ranking por estado",),
            )
        raise AssertionError("Schema estruturado inesperado")


class FakeModel:
    def with_structured_output(self, schema):
        return FakeRunnable(schema)


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
            """
        )


def test_grafo_descobre_interpreta_e_planeja(tmp_path: Path) -> None:
    db_path = tmp_path / "dados.db"
    _database(db_path)
    graph = build_graph(db_path, FakeModel())

    result = graph.invoke(
        {"question": "Quais estados tiveram mais clientes via App em maio?"}
    )

    assert result["intent"].metric == "clientes distintos"
    assert len(result["plan"].steps) == 2
    assert result["graph_steps"] == 3
    assert [event.node for event in result["trace"]] == [
        "discover_schema",
        "interpret_question",
        "plan_investigation",
    ]
