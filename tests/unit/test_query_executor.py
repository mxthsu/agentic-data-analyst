import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest

from data_analyst.database.executor import QueryExecutionError, execute_query


def _database(path: Path, rows: int = 3) -> None:
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE itens (id INTEGER PRIMARY KEY, nome TEXT)")
        db.executemany(
            "INSERT INTO itens (id, nome) VALUES (?, ?)",
            [(index, f"item-{index}") for index in range(1, rows + 1)],
        )


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_executa_select_parametrizado_e_limita_resultado(tmp_path: Path) -> None:
    path = tmp_path / "dados.db"
    _database(path, rows=4)

    result = execute_query(
        path,
        "SELECT id, nome FROM itens WHERE id >= :minimo ORDER BY id",
        params={"minimo": 2},
        row_limit=2,
    )

    assert result.columns == ("id", "nome")
    assert result.rows == ((2, "item-2"), (3, "item-3"))
    assert result.truncated is True
    assert result.duration_ms >= 0


def test_consulta_proibida_nao_altera_arquivo(tmp_path: Path) -> None:
    path = tmp_path / "dados.db"
    _database(path)
    before = _hash(path)

    with pytest.raises(QueryExecutionError):
        execute_query(path, "UPDATE itens SET nome = 'alterado'")

    assert _hash(path) == before


def test_query_longa_respeita_timeout(tmp_path: Path) -> None:
    path = tmp_path / "dados.db"
    _database(path)

    sql = """
    WITH RECURSIVE numeros(x) AS (
      SELECT 1
      UNION ALL
      SELECT x + 1 FROM numeros WHERE x < 100000000
    )
    SELECT SUM(x) AS total FROM numeros
    """

    with pytest.raises(QueryExecutionError, match="tempo"):
        execute_query(path, sql, timeout_seconds=0.001)
