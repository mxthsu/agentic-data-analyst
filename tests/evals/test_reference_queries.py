import sqlite3
from collections import defaultdict
from pathlib import Path

import pytest

DB_PATH = Path("data/anexo_desafio_1.db")
pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(),
    reason="SQLite do desafio não disponível localmente",
)


def _query(sql: str):
    with sqlite3.connect(DB_PATH) as db:
        return db.execute(sql).fetchall()


def test_top_estados_por_clientes_via_app_em_maio_de_2025() -> None:
    rows = _query(
        """
        SELECT c.estado, COUNT(DISTINCT c.id) AS clientes
        FROM clientes c
        JOIN compras p ON p.cliente_id = c.id
        WHERE p.canal = 'App'
          AND strftime('%Y-%m', p.data_compra) = '2025-05'
        GROUP BY c.estado
        ORDER BY clientes DESC, c.estado ASC
        LIMIT 5
        """
    )

    assert rows == [
        ("São Paulo", 6),
        ("Minas Gerais", 3),
        ("Santa Catarina", 3),
        ("Alagoas", 2),
        ("Espírito Santo", 2),
    ]


def test_clientes_que_interagiram_com_whatsapp_em_2024() -> None:
    rows = _query(
        """
        SELECT COUNT(DISTINCT cliente_id)
        FROM campanhas_marketing
        WHERE canal = 'WhatsApp'
          AND interagiu = 1
          AND strftime('%Y', data_envio) = '2024'
        """
    )

    assert rows == [(17,)]


def test_media_de_compras_por_cliente_em_cada_categoria() -> None:
    rows = _query(
        """
        SELECT categoria,
               ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT cliente_id), 3) AS media
        FROM compras
        GROUP BY categoria
        ORDER BY media DESC, categoria ASC
        """
    )

    assert rows == [
        ("Roupas", 2.211),
        ("Viagens", 2.162),
        ("Livros", 1.976),
        ("Serviços", 1.962),
        ("Eletrônicos", 1.923),
        ("Alimentos", 1.882),
    ]


def test_reclamacoes_nao_resolvidas_por_canal() -> None:
    rows = _query(
        """
        SELECT canal, COUNT(*) AS total
        FROM suporte
        WHERE tipo_contato = 'Reclamação'
          AND resolvido = 0
        GROUP BY canal
        ORDER BY total DESC, canal ASC
        """
    )

    assert rows == [("Telefone", 19), ("Chat", 18), ("E-mail", 14)]


def test_tendencia_de_reclamacoes_nos_ultimos_12_meses_disponiveis() -> None:
    rows = _query(
        """
        WITH limite AS (
            SELECT date(MAX(data_contato), 'start of month', '-11 months') AS inicio,
                   MAX(date(data_contato)) AS fim
            FROM suporte
        )
        SELECT strftime('%Y-%m', s.data_contato) AS mes,
               s.canal,
               COUNT(*) AS total
        FROM suporte s, limite l
        WHERE s.tipo_contato = 'Reclamação'
          AND date(s.data_contato) >= l.inicio
          AND date(s.data_contato) <= l.fim
        GROUP BY mes, s.canal
        ORDER BY mes, s.canal
        """
    )

    months = sorted({month for month, _, _ in rows})
    totals = defaultdict(int)
    for _, channel, total in rows:
        totals[channel] += total

    assert months == [
        "2024-08",
        "2024-09",
        "2024-10",
        "2024-11",
        "2024-12",
        "2025-01",
        "2025-02",
        "2025-03",
        "2025-04",
        "2025-05",
        "2025-06",
        "2025-07",
    ]
    assert dict(totals) == {"Chat": 34, "E-mail": 27, "Telefone": 33}
