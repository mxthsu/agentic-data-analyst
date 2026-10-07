from pathlib import Path

import pytest

from data_analyst.database.inspector import inspect_database

DB_PATH = Path("data/anexo_desafio_1.db")


@pytest.mark.skipif(not DB_PATH.exists(), reason="SQLite do desafio não disponível localmente")
def test_schema_real_diverge_do_enunciado_sem_quebrar_descoberta() -> None:
    schema = inspect_database(DB_PATH)

    assert set(schema.tables) == {
        "campanhas_marketing",
        "clientes",
        "compras",
        "suporte",
    }
    client_columns = {column.name for column in schema.tables["clientes"].columns}
    assert {"valor_total_gasto", "data_ultima_compra"} <= client_columns
    assert schema.date_coverage["compras.data_compra"].max_date == "2025-07-22"
