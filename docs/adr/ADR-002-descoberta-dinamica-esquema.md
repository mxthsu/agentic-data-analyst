# ADR-002 — Descoberta dinâmica do esquema

**Status:** Aceito
**Data:** 2026-10-06

## Contexto

O arquivo SQLite recebido contém colunas em `clientes` que não aparecem no enunciado. Uma solução baseada apenas no esquema descrito no PDF pode gerar consultas incorretas e não atende ao requisito de descoberta dinâmica.

## Decisão

Descobrir tabelas, colunas, tipos e chaves estrangeiras diretamente do SQLite em tempo de execução usando os metadados do próprio banco. Tabelas internas são ignoradas. A cobertura temporal relevante também é derivada dos dados para apoiar a interpretação de períodos.

## Alternativa considerada

Fixar o esquema no prompt. A implementação seria menor, porém frágil e já entraria em conflito com a amostra real.

## Consequências

O agente pode operar sobre pequenas mudanças de esquema sem alteração de código. Esquemas muito grandes exigiriam seleção de relevância em uma evolução futura.
