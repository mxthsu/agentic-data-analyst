from __future__ import annotations

from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError


@dataclass(frozen=True)
class SQLValidation:
    valid: bool
    reason: str | None = None


class SQLGuard:
    """Valida a forma da consulta antes de qualquer acesso ao SQLite."""

    _FORBIDDEN = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Create,
        exp.Drop,
        exp.Alter,
        exp.Command,
    )

    def validate(self, sql: str) -> SQLValidation:
        if not sql.strip():
            return SQLValidation(False, "Consulta vazia.")

        try:
            statements = [statement for statement in parse(sql, read="sqlite") if statement]
        except ParseError:
            return SQLValidation(False, "SQL inválido.")

        if len(statements) != 1:
            return SQLValidation(False, "Apenas uma instrução SQL é permitida.")

        statement = statements[0]
        if not isinstance(statement, exp.Query):
            return SQLValidation(False, "Somente consultas de leitura são permitidas.")

        if any(isinstance(node, self._FORBIDDEN) for node in statement.walk()):
            return SQLValidation(False, "A consulta contém operação não permitida.")

        normalized = sql.lstrip().upper()
        if normalized.startswith(("ATTACH", "DETACH", "PRAGMA")):
            return SQLValidation(False, "Comando SQLite não permitido.")

        limit = statement.args.get("limit")
        group = statement.args.get("group")
        order = statement.args.get("order")
        if limit is not None and group is not None:
            if order is None:
                return SQLValidation(
                    False,
                    "Rankings agregados com LIMIT exigem ORDER BY determinístico.",
                )
            if len(order.expressions) < 2:
                return SQLValidation(
                    False,
                    (
                        "Rankings agregados com LIMIT exigem um critério secundário "
                        "determinístico para desempates."
                    ),
                )

        return SQLValidation(True)

    def ensure_safe(self, sql: str) -> None:
        result = self.validate(sql)
        if not result.valid:
            raise SQLPolicyError(result.reason or "Consulta não permitida.")


class SQLPolicyError(ValueError):
    pass
