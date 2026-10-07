import sqlite3
from pathlib import Path

from data_analyst.database.inspector import inspect_database


def _create_database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                segmento TEXT,
                data_cadastro TEXT
            );
            CREATE TABLE compras (
                id INTEGER PRIMARY KEY,
                cliente_id INTEGER,
                data_compra TEXT,
                valor REAL,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            );
            INSERT INTO clientes (nome, segmento, data_cadastro)
            VALUES ('Cliente A', 'B2B', '2025-05-01');
            INSERT INTO compras VALUES (1, 1, '2025-05-10', 100.0);
            """
        )


def test_descobre_schema_real_coluna_extra_fk_e_datas(tmp_path: Path) -> None:
    db_path = tmp_path / "teste.db"
    _create_database(db_path)

    schema = inspect_database(db_path)

    assert set(schema.tables) == {"clientes", "compras"}
    assert "sqlite_sequence" not in schema.tables
    assert {column.name for column in schema.tables["clientes"].columns} >= {
        "id",
        "nome",
        "segmento",
    }

    fk = schema.tables["compras"].foreign_keys[0]
    assert (fk.column, fk.referenced_table, fk.referenced_column) == (
        "cliente_id",
        "clientes",
        "id",
    )

    coverage = schema.date_coverage["compras.data_compra"]
    assert coverage.min_date == "2025-05-10"
    assert coverage.max_date == "2025-05-10"
    assert coverage.years_by_month[5] == (2025,)

    assert schema.categorical_values["clientes.segmento"] == ("B2B",)
    assert "clientes.nome" not in schema.categorical_values
    assert "compras.cliente_id" not in schema.categorical_values


def test_descoberta_cita_identificadores_com_espaco(tmp_path: Path) -> None:
    db_path = tmp_path / "identificadores.db"
    with sqlite3.connect(db_path) as db:
        db.execute(
            'CREATE TABLE "pedido especial" '
            '("id pedido" INTEGER PRIMARY KEY, "data evento" TEXT)'
        )
        db.execute(
            'INSERT INTO "pedido especial" VALUES (?, ?)',
            (1, "2024-07-22"),
        )

    schema = inspect_database(db_path)

    assert "pedido especial" in schema.tables
    assert "pedido especial.data evento" in schema.date_coverage
