# ADR-003 — Segurança de SQL em camadas

**Status:** Aceito
**Data:** 2026-10-06

## Contexto

O SQL será proposto por um modelo e pode conter erros, múltiplas instruções ou comandos incompatíveis com um assistente analítico somente leitura.

## Decisão

Aplicar defesa em profundidade: SQLite aberto em modo somente leitura, `PRAGMA query_only=ON`, análise e validação estrutural com `sqlglot`, apenas uma consulta de leitura por etapa, autorizador do SQLite, limite de tempo e limite de linhas. Toda consulta reparada passa novamente pela validação.

## Alternativas consideradas

- Regex de palavras proibidas: simples, mas fácil de contornar e frágil com CTEs.
- Confiar apenas em `mode=ro`: protege o arquivo, porém não controla múltiplas instruções, custo da consulta ou formato aceito.

## Consequências

Há mais código determinístico, mas as invariantes de segurança ficam independentes do comportamento do modelo e podem ser testadas isoladamente.
