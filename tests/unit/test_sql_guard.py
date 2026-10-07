import pytest

from data_analyst.safety.sql_guard import SQLGuard, SQLPolicyError


@pytest.fixture
def guard() -> SQLGuard:
    return SQLGuard()


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT id, nome FROM clientes",
        "WITH ativos AS (SELECT id FROM clientes) SELECT * FROM ativos",
        "SELECT COUNT(*) AS total FROM compras",
    ],
)
def test_aceita_consultas_de_leitura(guard: SQLGuard, sql: str) -> None:
    assert guard.validate(sql).valid is True


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE clientes SET nome = 'x'",
        "DELETE FROM clientes",
        "DROP TABLE clientes",
        "ATTACH DATABASE 'outro.db' AS outro",
        "PRAGMA journal_mode=WAL",
        "SELECT 1; SELECT 2",
    ],
)
def test_rejeita_operacoes_fora_da_politica(guard: SQLGuard, sql: str) -> None:
    result = guard.validate(sql)

    assert result.valid is False
    with pytest.raises(SQLPolicyError):
        guard.ensure_safe(sql)
